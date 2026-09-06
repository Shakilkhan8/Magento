import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from contextlib import contextmanager
from odoo.exceptions import UserError
from odoo.addons.mail.models.mail_thread import MailThread

_logger = logging.getLogger(__name__)


@contextmanager
def _suppress_email_config_error():
    """
    IMR Pick/Out backorder create/confirm karte waqt agar Odoo internally
    kahin bhi message_post() call kare aur sender ka email set na hone ki
    wajah se "Unable to send message, please configure the sender's
    email address." UserError raise ho, to us error ko silently ignore
    kar dete hain (sirf notification skip hoti hai) - baqi operation
    (picking/move create, confirm, assign) normal chalta rehta hai.
    Koi aur (unrelated) error normally raise hoga, wo yahan swallow
    nahi hoti.

    NOTE: Ye MailThread.message_post ko temporarily patch karta hai -
    sirf isi block ke andar, finally mein wapas original par restore
    ho jata hai. Multi-worker (prefork) Odoo mein safe hai kyunki har
    request apne alag process mein handle hoti hai; agar aap gevent /
    threaded (longpolling) worker use kar rahe hain to isay ek lock
    ke sath aur bhi safe banaya ja sakta hai - zaroorat ho to bata dein.
    """
    original_message_post = MailThread.message_post

    def _safe_message_post(self, *args, **kwargs):
        try:
            return original_message_post(self, *args, **kwargs)
        except UserError as e:
            if 'configure the sender' in str(e):
                _logger.warning(
                    "Message post skipped (sender email not configured) on %s",
                    self
                )
                # NOTE: False return NAHI karna - Odoo ke core code mein
                # kahin kahin 'messages_all += record.message_post(...)'
                # jaisa recordset-concatenation hota hai. False us par
                # crash karta hai ('mail.message() + False'). Isliye
                # empty mail.message recordset return karo - ye
                # falsy bhi hai (bool check mein False jaisa) aur
                # concatenation-safe bhi.
                return self.env['mail.message']
            raise

    MailThread.message_post = _safe_message_post
    try:
        yield
    finally:
        MailThread.message_post = original_message_post

DB = 'shakilkhan8-magento-uat-31383000'
UserName = 'api'
Password = 'admin'

BASE_URL = 'https://shakilkhan8-magento-uat-31383000.dev.odoo.com'
AUTH_URL = '/web/session/authenticate'
SALE_ORDER_URL = '/api/create-sale-order'
SALE_ORDER_UPDATE_URL = '/api/update-sale-order'

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    extra_delivery_qty = fields.Float(
        string='Extra Delivery Qty (IMR)',
        compute='_compute_extra_delivery_qty',
        store=True,
        readonly=False,
        help="Quantity that must come from IMR warehouse if other warehouses are short."
    )

    price_unit_discounted = fields.Float()

    aladin_qty = fields.Float(
        string='Aladin Qty'
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Line create hotay hi turant compute karwa dein,
        # taake confirm ke waqt stock reserve hone se pehle
        # exist_qty / imr_qty ki sahi value store ho jaye
        lines._compute_extra_delivery_qty()
        return lines

    @api.depends('product_uom_qty', 'product_id', 'order_id.company_id')
    def _compute_extra_delivery_qty(self):
        imr_warehouse = self.env['stock.warehouse'].sudo().search([
            ('code', '=', 'IMR')
        ], limit=1)

        for line in self:
            if not line.product_id or line.product_id.type != 'product' or not imr_warehouse:
                line.extra_delivery_qty = 0.0
                continue

            own_warehouses = self.env['stock.warehouse'].sudo().search([
                ('id', '!=', imr_warehouse.id),
                ('company_id', '=', line.order_id.company_id.id)
            ])

            imr_qty = self.env['stock.quant'].search([
                ('warehouse_id', 'in', imr_warehouse.ids),
                ('product_id', '=', line.product_id.id),
            ])

            exist_qty = self.env['stock.quant'].search([
                ('warehouse_id', 'in', own_warehouses.ids),
                ('product_id', '=', line.product_id.id),
            ])

            exist_qty = sum(exist_qty.mapped('inventory_quantity_auto_apply')) -  sum(exist_qty.mapped('reserved_quantity'))
            imr_qty = sum(imr_qty.mapped('inventory_quantity_auto_apply')) -  sum(imr_qty.mapped('reserved_quantity'))

            if line.product_id.api_id and line.product_id.sync_on:

                if exist_qty > 0 and line.product_uom_qty <= exist_qty:
                   line.aladin_qty = line.product_uom_qty
                   line.extra_delivery_qty = 0.0

                elif imr_qty > 0 and line.product_uom_qty <= imr_qty:
                    line.aladin_qty = 0.0
                    line.extra_delivery_qty = line.product_uom_qty

                elif exist_qty > 0 and imr_qty > 0:
                    line.aladin_qty = exist_qty
                    line.extra_delivery_qty = line.product_uom_qty - exist_qty

                elif exist_qty == 0 and imr_qty > 0:
                    line.extra_delivery_qty = line.product_uom_qty

                else:
                    line.extra_delivery_qty = line.product_uom_qty
            else:
                line.aladin_qty = line.product_uom_qty



    def _prepare_invoice_line(self, **optional_values):

        res = super()._prepare_invoice_line(**optional_values)
        if res:
            res['extra_delivery_qty'] = self.extra_delivery_qty

        return res


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    api_order_id = fields.Integer(
        string='API Order ID'
    )



    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.order_line._compute_extra_delivery_qty()
        return orders

    def action_confirm(self):
        res = super().action_confirm()
        api_config = self.env['api.configuration'].sudo().search([], limit=1)
        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters !')

        for order in self:
                order._process_extra_delivery_qty()
        #
        self._send_sale_order_to_db2(params=api_config)
        return res

    def _process_extra_delivery_qty(self):
        # NOTE: Naye IMR backorder Pick/Out banate waqt Odoo (kabhi kabhi
        # apne core code se, jispe humara control nahi) message_post()
        # call kar sakta hai (backorder note / tracking waghera). Agar
        # sender ka email address configured nahi hai to ye
        # "Unable to send message, please configure the sender's email
        # address." UserError raise kar deta hai aur poori transaction
        # (picking + backorder creation sab) rollback ho jaati hai.
        #
        # Requirement: email bhejne ki koshish hi na ho, sirf
        # picking/backorder create ho jaye - is liye poore operation ko
        # _suppress_email_config_error() context manager mein wrap kar
        # dete hain jo sirf isi specific email-config error ko silently
        # ignore karta hai (message post skip ho jayega, lekin baqi
        # operation - picking/move create/confirm/assign - normal chalega).
        # Koi aur genuine error ho to wo normally raise hoga.
        self = self.with_context(
            mail_notify_force_send=False,
            tracking_disable=True,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
        )
        with _suppress_email_config_error():
            for picking in self.picking_ids.filtered(
                    lambda p: p.state not in ('done', 'cancel') and p.picking_type_id.code == 'outgoing'
            ):
                moves = picking.move_ids.filtered(lambda m: m.sale_line_id)

                # ---- STEP 0 (NAYA): Mixed lines handle karo ----
                # Jab ek hi sale line par aladin_qty > 0 AND extra_delivery_qty > 0
                # dono ho, to us line ka move ek hi waqt mein "extra" aur "normal"
                # dono nahi ho sakta -> isliye pehle qty-wise split karte hain.
                # Split ke baad har move (purana + naya) apne move-level
                # aladin_qty / extra_delivery_qty fields se independently
                # classify hoga, is liye niche wala logic sale_line ki bajaye
                # MOVE-level fields check karta hai.
                mixed_moves = moves.filtered(
                    lambda m: m.sale_line_id.aladin_qty > 0 and m.sale_line_id.extra_delivery_qty > 0
                )
                for move in mixed_moves:
                    self._split_move_chain_for_extra_qty(move)

                # Split hone ke baad moves dobara fetch karo (naye moves bhi
                # isi picking mein aa gaye honge, kyunki copy() picking_id
                # override nahi karta)
                moves = picking.move_ids.filtered(lambda m: m.sale_line_id)

                # ---- Classification ab MOVE-level fields se (sale_line se nahi) ----
                extra_moves = moves.filtered(lambda m: m.extra_delivery_qty > 0)
                normal_moves = moves - extra_moves

                if not extra_moves:
                    continue  # Scenario: sab normal -> Odoo ka apna flow

                if not normal_moves:
                    # Scenario: sab lines extra -> existing Pick+Out ko IMR mein convert karo
                    self._convert_picking_to_imr(picking, extra_moves)
                else:
                    # Scenario: mix -> naya IMR Pick+Out banao, normal wali WH mein rehne do
                    self._split_picking_for_extra(picking, extra_moves)
                    picking.action_assign()

    def _split_move_chain_for_extra_qty(self, out_move):
        """
        NAYI METHOD - Scenario 3 (mixed line):
        Ek hi sale line par aladin_qty > 0 AND extra_delivery_qty > 0 dono
        hon, to is move ko do hisso mein split karte hain:
          - extra_delivery_qty wala hissa -> naya move (aage IMR mein jayega)
          - aladin_qty wala hissa         -> purana move (normal delivery mein rahega)

        Sath hi is out_move se linked upstream PICK move ko bhi usi qty se
        split karte hain, taake naya Pick -> naya Out ka chain sahi bane
        (warna baqi IMR conversion logic move_orig_ids se galat/pura pick
        move utha legi).

        NOTE: Ye assume karta hai ke stock.move par 'aladin_qty' aur
        'extra_delivery_qty' fields already move creation ke waqt sale
        line se sync ho rahe hain (aapke bataye mutabiq ye fields
        stock.move par bhi add hain). Agar abhi sync nahi ho rahe, to
        move create/write hote waqt in dono fields ko sale_line se copy
        karna hoga (onchange/override _prepare_procurement_values waghera
        mein) - warna niche wala classification kaam nahi karega.
        """
        line = out_move.sale_line_id
        extra_qty = line.extra_delivery_qty
        aladin_qty = line.aladin_qty

        # Move ki UoM sale line se different ho sakti hai, is liye convert karo
        extra_qty_move_uom = line.product_uom._compute_quantity(extra_qty, out_move.product_uom)

        if extra_qty_move_uom <= 0 or extra_qty_move_uom >= out_move.product_uom_qty:
            # Invalid split (0 ya poora move hi extra) - kuch mat karo
            return

        remaining_qty = out_move.product_uom_qty - extra_qty_move_uom

        # ---- OUT move split ----
        new_out_move = out_move.copy({
            'product_uom_qty': extra_qty_move_uom,
            'state': 'draft',
            'aladin_qty': 0,
            'extra_delivery_qty': extra_qty,
            'move_orig_ids': [(5, 0, 0)],  # niche pick split ke baad link karenge
        })
        out_move.write({
            'product_uom_qty': remaining_qty,
            'aladin_qty': aladin_qty,
            'extra_delivery_qty': 0,
        })

        # ---- Corresponding PICK move(s) bhi split karo ----
        pick_moves = out_move.move_orig_ids
        for pick_move in pick_moves:
            extra_qty_pick_uom = line.product_uom._compute_quantity(extra_qty, pick_move.product_uom)
            if extra_qty_pick_uom <= 0 or extra_qty_pick_uom >= pick_move.product_uom_qty:
                continue

            remaining_pick_qty = pick_move.product_uom_qty - extra_qty_pick_uom

            new_pick_move = pick_move.copy({
                'product_uom_qty': extra_qty_pick_uom,
                'state': 'draft',
                'aladin_qty': 0,
                'extra_delivery_qty': extra_qty,
                'move_dest_ids': [(6, 0, [new_out_move.id])],
            })
            pick_move.write({
                'product_uom_qty': remaining_pick_qty,
                'aladin_qty': aladin_qty,
                'extra_delivery_qty': 0,
            })

            new_out_move.write({'move_orig_ids': [(4, new_pick_move.id)]})

            new_pick_move._action_confirm()
            new_pick_move._action_assign()

        new_out_move._action_confirm()
        new_out_move._action_assign()

    def _convert_picking_to_imr(self, picking, extra_moves):
        """
        Scenario 2: Jab poori delivery hi extra ho, to existing Pick + Out ko
        IMR warehouse mein convert karte hain - bina naya record banaye.
        """
        imr_pick_type, imr_out_type = self._get_imr_picking_types()

        pick_moves = extra_moves.move_orig_ids
        pick_pickings = pick_moves.picking_id

        # ---- Existing Pick(s) ko IMR mein convert karo ----
        for pick_picking in pick_pickings:
            moves_of_this_picking = pick_picking.move_ids

            # 1) Moves ko detach karo -> picking khali ho jayegi -> state = draft
            moves_of_this_picking.write({'picking_id': False})

            # 2) Ab picking draft hai, picking_type/location change kar sakte hain
            pick_picking.write({
                'picking_type_id': imr_pick_type.id,
                'location_id': imr_pick_type.default_location_src_id.id,
                'location_dest_id': imr_pick_type.default_location_dest_id.id,
                'is_backorder': True,
            })

            # 3) Moves ko wapas attach karo, nayi locations ke sath
            moves_of_this_picking.write({
                'picking_id': pick_picking.id,
                'location_id': imr_pick_type.default_location_src_id.id,
                'location_dest_id': imr_pick_type.default_location_dest_id.id,
            })

            pick_picking.action_confirm()
            pick_picking.action_assign()

        # ---- Existing Out ko IMR mein convert karo ----
        out_moves = picking.move_ids

        out_moves.write({'picking_id': False})

        picking.write({
            'picking_type_id': imr_out_type.id,
            'location_id': imr_out_type.default_location_src_id.id,
            'is_backorder': True,
        })

        out_moves.write({
            'picking_id': picking.id,
            'location_id': imr_out_type.default_location_src_id.id,
        })

        picking.action_confirm()
        picking.action_assign()

    def _split_picking_for_extra(self, picking, extra_moves):
        """Scenario 1 (mix): pehle jaisa hi - naya IMR Pick+Out copy karke banate hain."""
        imr_pick_type, imr_out_type = self._get_imr_picking_types()

        extra_pick_moves = extra_moves.move_orig_ids
        original_pick_pickings = extra_pick_moves.picking_id

        for pick_picking in original_pick_pickings:
            pick_backorder = pick_picking.copy({
                'move_ids': [],
                'move_line_ids': [],
                'move_type': pick_picking.move_type,
                'backorder_id': pick_picking.id,
                'origin': pick_picking.origin,
                'state': 'draft',
                'is_backorder': True,
                'picking_type_id': imr_pick_type.id,
                'location_id': imr_pick_type.default_location_src_id.id,
                'location_dest_id': imr_pick_type.default_location_dest_id.id,
            })
            moves_from_this_picking = extra_pick_moves.filtered(lambda m: m.picking_id == pick_picking)
            moves_from_this_picking.write({
                'picking_id': pick_backorder.id,
                'location_id': pick_backorder.location_id.id,
                'location_dest_id': pick_backorder.location_dest_id.id,
            })
            pick_backorder.action_confirm()
            pick_backorder.action_assign()

        out_backorder = picking.copy({
            'move_ids': [],
            'move_line_ids': [],
            'move_type': picking.move_type,
            'backorder_id': picking.id,
            'origin': picking.origin,
            'state': 'draft',
            'is_backorder': True,
            'carrier_id': picking.carrier_id.id,
            'picking_type_id': imr_out_type.id,
            'location_id': imr_out_type.default_location_src_id.id,
            'location_dest_id': picking.location_dest_id.id,
        })
        extra_moves.write({
            'picking_id': out_backorder.id,
            'location_id': out_backorder.location_id.id,
        })
        out_backorder.action_confirm()
        out_backorder.action_assign()

        # Normal wali purani pickings (Pick) refresh
        original_pick_pickings.action_assign()

    def _get_imr_picking_types(self):
        imr_warehouse = self.env['stock.warehouse'].search([('code', '=', 'IMR')], limit=1)
        if not imr_warehouse:
            raise UserError('IMR warehouse configured nahi hai — pehle setup karein.')
        if imr_warehouse.delivery_steps != 'pick_ship':
            raise UserError(f'IMR warehouse ({imr_warehouse.name}) 2-step delivery configured nahi hai.')
        imr_pick_type = imr_warehouse.pick_type_id
        imr_out_type = imr_warehouse.out_type_id
        if not imr_pick_type or not imr_out_type:
            raise UserError(f'IMR warehouse ({imr_warehouse.name}) mein Pick/Out operation types missing hain.')
        return imr_pick_type, imr_out_type



    def get_session_id(self):
        api_config = self.env['api.configuration'].sudo().search([], limit=1)
        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters !')

        url = api_config.url + AUTH_URL
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": api_config.db_name,
                "login": api_config.user_name,
                "password": api_config.password,
            }
        }
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.request(method='GET', url=url, headers=headers, json=payload)
        if response.status_code == 200 and response.cookies.values():
            session_id = response.cookies.values()[0]

            headers['Token_id'] = session_id
            return session_id
        else:
            return None


    def _send_sale_order_to_db2(self, params=None):

        BASE_URL = params.url

        session = requests.Session()

        session_id = self.get_session_id()

        if not session_id:
            _logger.error("DB2 auth failed: could not obtain session_id")
            return

        order_lines = []
        for line in self.order_line:
            tmpl_api_id = line.product_id.product_tmpl_id.api_id

            if not tmpl_api_id:
                _logger.warning(
                    "Product '%s' has no api_id (not synced to DB2 yet), skipping line.",
                    line.product_id.display_name
                )
                continue

            percentage = self.env['profit.margin.categories'].search([
                ('category_id', '=', line.product_id.categ_id.id),
                ('state', '=', 'confirm')
            ], limit=1)

            price = line.product_id.standard_price or 0
            if percentage:
                price = (line.product_id.standard_price * percentage.percentage / 100) + line.product_id.standard_price

            order_lines.append({
                'product_id': line.product_id.api_id,
                'product_uom_qty': line.extra_delivery_qty,
                'name': line.name,
                'price_unit': price if price else line.product_id.standard_price,
            })

        if not order_lines:
            _logger.warning("No valid lines to send for order %s", self.name)
            return

        headers = {
            'Authorization': f'Bearer {session_id}',
            'Content-Type': 'application/json',
        }

        picking = False
        shipping_info = {}

        partner_info = {
            'name': self.partner_id.name,
            'street': self.partner_id.street,
            'street2': self.partner_id.street2,
            'city': self.partner_id.city,
            'zip': self.partner_id.zip,
            'country': self.partner_id.country_id.name,
            'state': self.partner_id.state_id.name,
            'phone': self.partner_id.phone,
            'mobile': self.partner_id.mobile,
            'email': self.partner_id.email,
            'vat': self.partner_id.vat,
        }

        if self.picking_ids:
            picking = self.picking_ids[0]
            shipping_info['carrier_id'] = picking.carrier_id.name
            shipping_info['weight'] = picking.weight or 0
            shipping_info['shipping_weight'] = picking.shipping_weight or 0
            shipping_info['move_type'] = picking.move_type or 'direct'

        try:
            sale_response = requests.post(
                BASE_URL + SALE_ORDER_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "data": {
                            'partner_info': partner_info,
                            'shipping_info': shipping_info,
                            "order_id": self.id,
                            "lines": order_lines,
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                },
                cookies={
                    "session_id": session_id,
                },
                timeout=30,
            )
            sale_response.raise_for_status()
            result = sale_response.json()

        except requests.exceptions.RequestException as e:
            _logger.error("DB2 sale order request failed for order %s: %s", self.name, e)
            return

        # JSON-RPC always returns a "result" key, but its value can legitimately
        # be None/null if the receiving controller errored out silently or
        # returned nothing - guard against that instead of assuming a dict.
        rpc_result = result.get('result') or {}

        if not isinstance(rpc_result, dict):
            _logger.error(
                "DB2 sale order creation for %s returned an unexpected response: %s",
                self.name, result
            )
            return

        if 'error' in result:
            # JSON-RPC level error (e.g. auth issue, uncaught exception)
            _logger.error("DB2 JSON-RPC error for order %s: %s", self.name, result.get('error'))
            return

        if 'sale_order_id' in rpc_result:
            self.api_order_id = rpc_result['sale_order_id']

        _logger.info("DB2 sale order id: %s", rpc_result.get('sale_order_id'))

        if rpc_result.get('status') == 200:
            _logger.info(
                "Sale order %s sent to DB2 successfully: %s",
                self.name, rpc_result.get('message'),
            )
        else:
            _logger.error("DB2 sale order creation failed for %s: %s", self.name, rpc_result)
