from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)
from collections import defaultdict

class ProductAPI(http.Controller):

    @http.route('/api/create_product', type='json', auth='public', methods=['POST'], csrf=False)
    def create_product(self, **kwargs):
        try:
            vals = request.httprequest.json.get('data', {})

            ProductTemplate = request.env['product.template'].sudo()
            template = ProductTemplate.search([
                ('api_id', '=', vals.get('api_id'))
            ], limit=1)

            if vals.get('barcode'):
                existing_barcode = ProductTemplate.search([
                    ('barcode', '=', vals.get('barcode')),
                    ('id', '!=', template.id if template else 0)
                ], limit=1)
                if existing_barcode:
                    return {
                        'status': 'error',
                        'message': f"Barcode {vals.get('barcode')} already used by product {existing_barcode.id} ({existing_barcode.name})"
                    }

            template_vals = {
                'name': vals.get('name'),
                'list_price': vals.get('lst_price', 0),
                'image_1920': vals.get('template_image', False),
                'detailed_type': vals.get('detailed_type'),
                'default_code': vals.get('default_code'),
                'barcode': vals.get('barcode'),
                'api_id': vals.get('api_id'),
                'standard_price': vals.get('standard_price'),
                'sync_on': vals.get('sync_on', False),
                'weight': vals.get('weight', 0),
            }

            if template:
                template.write(template_vals)
            else:
                template = ProductTemplate.create(template_vals)

            return {
                'status': 'success',
                'product_id': template.id,
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/create-product-variant', type='json', auth='public', methods=['POST'], csrf=False)
    def create_product_variant(self, **kwargs):

        data = request.httprequest.json.get('data', {})

        template = request.env["product.template"].sudo().search(
            [("api_id", "=", data.get("api_id"))],
            limit=1
        )

        if not template:
            return {
                "success": False,
                "message": "Product template not found."
            }

        grouped_attributes = defaultdict(list)

        for line in data.get("attribute_values", []):

            attribute = request.env["product.attribute"].sudo().search(
                [("name", "=", line["attribute"])],
                limit=1
            )

            if not attribute:
                attribute = request.env["product.attribute"].sudo().create({
                    "name": line["attribute"],
                    "create_variant": "always",
                })

            value = request.env["product.attribute.value"].sudo().search(
                [
                    ("attribute_id", "=", attribute.id),
                    ("name", "=", line["value"])
                ],
                limit=1
            )

            if not value:
                value = request.env["product.attribute.value"].sudo().create({
                    "attribute_id": attribute.id,
                    "name": line["value"],
                })
            grouped_attributes[attribute.id].append(value.id)

        vals = {
            "attribute_line_ids": []
        }

        for attribute_id, value_ids in grouped_attributes.items():
            existing_line = template.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == attribute_id
            )

            if existing_line:
                # Existing values
                old_values = existing_line.value_ids.ids

                # Merge new values
                new_values = list(set(old_values + value_ids))

                existing_line.write({
                    "value_ids": [(6, 0, new_values)]
                })

            else:
                vals["attribute_line_ids"].append(
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute_id,
                            "value_ids": [(6, 0, value_ids)]
                        }
                    )
                )

        if vals["attribute_line_ids"]:
            template.write(vals)

            # Ye ab hamesha chalega - single product (no attributes) ke case mein bhi,
            # kyunke template.product_variant_ids pehle se hi 1 default variant rakhta hai
        variant_ids = data.get('variant_ids') or []
        for rec in sorted(template.product_variant_ids):
            if not variant_ids:
                break
            rec.write({
                'api_id': variant_ids.pop(0),
                'sync_on': template.sync_on,  # sync_on bhi yahi se propagate karo
            })

        return {
            'message': template.product_variant_ids.ids
        }

    @http.route('/api/update-product-images', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_images(self, **kwargs):


        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals and 'default_code' in vals:
                default_code = vals.get('default_code')
                product = request.env['product.product'].sudo().search([
                    ('default_code', '=', default_code)
                ], limit=1)

                if not product:
                    return {'status': 'error', 'message': 'Product not found'}
                else:
                    product.sudo().write({
                        'image_1920': vals.get('image_1920') if vals.get('image_1920') else product.image_1920,
                        'api_id': vals.get('product_id')
                    })

                    return {
                        'status': 'success',
                        'message': {
                            'barcode': product.barcode,
                            'list_price': product.list_price,
                        }
                    }

        except Exception as e:

            return {'status': 'error', 'message': str(e)}

    @http.route('/api/update-product-template', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_template(self, **kwargs):

        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals:
                product_id = vals.get('product_id')
                product = request.env['product.template'].sudo().search([
                    ('api_id', '=', product_id)
                ], limit=1)

                if not product:
                    return {'status': 'error', 'message': 'Product not found'}
                else:
                    product.sudo().write({
                        'image_1920': vals.get('image_1920') if vals.get('image_1920') else product.image_1920,
                        'barcode': vals.get('barcode', False),
                        'list_price': vals.get('lst_price', 0),
                        'detailed_type': vals.get('detailed_type', False),
                        'name': vals.get('name', False),
                        'standard_price': vals.get('standard_price'),
                        'sync_on': vals.get('sync_on', False),
                        'weight': vals.get('weight', 0),
                    })


                    return {
                        'status': 'success',
                        'message': {
                            'barcode': product.barcode,
                            'list_price': product.list_price,
                            'name': product.name,
                        }
                    }

        except Exception as e:

            return {'status': 'error', 'message': str(e)}

    @http.route('/api/update-product-variant', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_variants(self, **kwargs):

        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals:
                product_id = vals.get('product_id')
                product = request.env['product.product'].sudo().search([
                    ('api_id', '=', product_id)
                ], limit=1)

                if not product:
                    return {'status': 'error', 'message': 'Product not found'}
                else:
                    product.sudo().write({
                        'api_id': vals.get('product_id'),
                        'image_1920': vals.get('image_1920', False) if vals.get('image_1920',
                                                                                False) else product.image_1920,
                        'barcode': vals.get('barcode', False),
                        'lst_price': vals.get('lst_price', 0),
                        'detailed_type': vals.get('detailed_type', False),
                        'name': vals.get('name', False),
                        'standard_price': vals.get('standard_price'),
                        'default_code': vals.get('default_code'),
                        'sync_on': vals.get('sync_on', False),
                        'weight': vals.get('weight', 0),
                    })

                    # Warehouse
                    warehouse = request.env['stock.warehouse'].sudo().search([
                        ('code', '=', 'IMR')
                    ], limit=1)

                    if not warehouse:
                        warehouse = warehouse.sudo().create({
                            'name': 'Imran WH',
                            'code': 'IMR'
                        })
                        return {'status': 'error', 'message': 'Warehouse not found'}

                    location = warehouse.lot_stock_id

                    # Inventory adjustments only apply when inventory_mode=True (stock.quant inverse).
                    inv_ctx = dict(request.env.context or {}, inventory_mode=True)
                    Quant = request.env['stock.quant'].sudo().with_context(inv_ctx)

                    quant = Quant.search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', location.id),
                    ], limit=1)

                    qty = vals.get('qty')
                    if not quant:
                        quant = Quant.create({
                            'product_id': product.id,
                            'location_id': location.id,
                        })

                    # Check for tracking
                    if product.tracking != 'none':
                        return {'status': 'error',
                                'message': f'Product  is tracked by {product.tracking}. Lot/Serial required.'}

                    # Sets counted qty and creates stock moves (Directly apply as SUPERUSER to bypass permission/UI checks).
                    from odoo import SUPERUSER_ID
                    quant.with_user(SUPERUSER_ID).write({'inventory_quantity': qty})
                    quant.with_user(SUPERUSER_ID)._apply_inventory()

                    return {
                        'status': 'success',
                        'message': {
                            'barcode': product.barcode,
                            'list_price': product.list_price,
                            'name': product.name,
                        }
                    }

        except Exception as e:

            return {'status': 'error', 'message': str(e)}

    import logging
    _logger = logging.getLogger(__name__)

    @http.route('/api/update-delivery', type='json', auth='public', methods=['POST'], csrf=False)
    def update_delivery(self, **kwargs):
        try:
            vals = request.httprequest.json.get('data', {})

            order = request.env['sale.order'].sudo()
            order = order.sudo().search([('id', '=', vals.get('order_id'))], limit=1)

            if not order:
                return {'status': 'error', 'message': 'Order not found'}

            has_picked_field = 'picked' in request.env['stock.move.line']._fields

            # extra_delivery_qty lives on stock.move (related from
            # sale_line_id.extra_delivery_qty, stored). Also check move
            # line just in case it's duplicated there in some flows.
            move_has_extra_qty = 'extra_delivery_qty' in request.env['stock.move']._fields
            move_line_has_extra_qty = 'extra_delivery_qty' in request.env['stock.move.line']._fields

            results = {}  # keyed by picking_id so we can update across passes

            def picking_has_extra_qty(picking):
                """
                Returns True if any move (or move line) on this picking
                carries a positive extra_deliver_qty - meaning this is the
                delivery that should receive the carrier_tracking_ref.
                """
                for move in picking.move_ids_without_package:
                    if move_has_extra_qty and (move.extra_delivery_qty or 0) > 0:
                        return True
                    if move_line_has_extra_qty:
                        for ml in move.move_line_ids:
                            if (ml.extra_delivery_qty or 0) > 0:
                                return True
                return False

            def process_move_lines(picking):
                """Set quantities / lots on move lines for a picking that is ready to go."""
                move_debug = []
                for move in picking.move_ids_without_package:
                    if move.state in ('cancel', 'done'):
                        continue

                    qty = move.product_uom_qty
                    product = move.product_id

                    # ---- Lot/Serial tracking check ----
                    lot = False
                    if product.tracking != 'none':
                        quant = request.env['stock.quant'].sudo().search([
                            ('product_id', '=', product.id),
                            ('location_id', '=', move.location_id.id),
                            ('quantity', '>', 0),
                            ('lot_id', '!=', False),
                        ], limit=1)
                        if quant:
                            lot = quant.lot_id

                    move_debug.append({
                        'product': product.name,
                        'tracking': product.tracking,
                        'demand_qty': qty,
                        'lot_found': lot.name if lot else None,
                        'move_state_before': move.state,
                    })

                    # ---- Existing move lines ----
                    if move.move_line_ids:
                        move_line = move.move_line_ids[0]
                        move_line.quantity = qty
                        if has_picked_field:
                            move_line.picked = True
                        if lot:
                            move_line.lot_id = lot.id

                        # Agar multiple lines hain to baaki zero kar do
                        for extra_line in move.move_line_ids[1:]:
                            extra_line.quantity = 0

                    else:
                        line_vals = {
                            'move_id': move.id,
                            'picking_id': picking.id,
                            'product_id': product.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'quantity': qty,
                        }
                        if has_picked_field:
                            line_vals['picked'] = True
                        if lot:
                            line_vals['lot_id'] = lot.id

                        request.env['stock.move.line'].sudo().create(line_vals)

                return move_debug

            def validate_picking(picking):
                """Run button_validate + resolve any wizard that pops up."""
                result = picking.sudo().with_context(
                    skip_backorder=True,
                    picking_ids_not_to_backorder=picking.ids,
                    skip_overprocessed_check=True,
                    skip_immediate=True,
                    skip_sms=True,
                    skip_send_sms=True,
                ).button_validate()

                wizard_triggered = None
                if isinstance(result, dict):
                    wizard_triggered = result.get('res_model')
                    wizard_context = result.get('context', {})

                    _logger.warning(
                        "Picking %s: wizard triggered -> %s | context: %s",
                        picking.name, wizard_triggered, wizard_context
                    )

                    if wizard_triggered == 'stock.backorder.confirmation':
                        backorder_wizard = request.env['stock.backorder.confirmation'].sudo().with_context(
                            wizard_context
                        ).create({})
                        backorder_wizard.process()

                    elif wizard_triggered == 'stock.overprocessed.transfer':
                        over_wizard = request.env['stock.overprocessed.transfer'].sudo().with_context(
                            wizard_context
                        ).create({})
                        over_wizard.action_confirm()

                    elif wizard_triggered == 'stock.immediate.transfer':
                        immediate_wizard = request.env['stock.immediate.transfer'].sudo().with_context(
                            wizard_context
                        ).create({})
                        immediate_wizard.process()

                    elif wizard_triggered == 'confirm.stock.sms':
                        sms_wizard = request.env['confirm.stock.sms'].sudo().with_context(
                            wizard_context
                        ).create({})
                        if hasattr(sms_wizard, 'action_skip'):
                            sms_wizard.action_skip()
                        elif hasattr(sms_wizard, 'action_confirm'):
                            sms_wizard.action_confirm()

                    # Skip ke baad state phir bhi na badle to, ek aakhri validate try karo
                    picking.invalidate_recordset()
                    if picking.state not in ('done', 'cancel'):
                        picking.sudo().with_context(
                            skip_backorder=True,
                            picking_ids_not_to_backorder=picking.ids,
                            skip_overprocessed_check=True,
                            skip_immediate=True,
                            skip_sms=True,
                            skip_send_sms=True,
                        ).button_validate()

                picking.invalidate_recordset()
                return wizard_triggered

            def handle_picking(picking):
                """
                Handles a single BACKORDER (is_backorder=True) picking based on
                its CURRENT state. Returns True if this picking made progress
                (was validated / already done / cancelled), False if it is
                still waiting on a prior operation.
                """
                picking.invalidate_recordset()

                # ---- Assign carrier_tracking_ref ONLY to the picking that
                #      actually carries the extra_deliver_qty line(s). ----
                gets_tracking_ref = picking_has_extra_qty(picking)
                if gets_tracking_ref and vals.get('carrier_tracking_ref'):
                    picking.sudo().write({
                        'carrier_tracking_ref': vals.get('carrier_tracking_ref')
                    })
                    picking.invalidate_recordset()

                if picking.state == 'draft':
                    picking.action_confirm()
                    picking.invalidate_recordset()

                if picking.state == 'done':
                    results[picking.id] = {
                        'picking_id': picking.id,
                        'picking_name': picking.name,
                        'state': picking.state,
                        'has_extra_qty': gets_tracking_ref,
                        'note': 'already done',
                    }
                    return True

                if picking.state == 'cancel':
                    results[picking.id] = {
                        'picking_id': picking.id,
                        'picking_name': picking.name,
                        'state': picking.state,
                        'has_extra_qty': gets_tracking_ref,
                        'note': 'cancelled - skipped',
                    }
                    return True

                if picking.state == 'waiting':
                    # Previous operation (e.g. Pick) not done yet - can't process this one now
                    results[picking.id] = {
                        'picking_id': picking.id,
                        'picking_name': picking.name,
                        'state': picking.state,
                        'has_extra_qty': gets_tracking_ref,
                        'note': 'waiting on previous operation',
                    }
                    return False

                if picking.state not in ('assigned', 'confirmed', 'partially_available'):
                    # e.g. still not reservable - report and skip for now
                    results[picking.id] = {
                        'picking_id': picking.id,
                        'picking_name': picking.name,
                        'state': picking.state,
                        'has_extra_qty': gets_tracking_ref,
                        'note': 'not ready to process',
                    }
                    return False

                move_debug = process_move_lines(picking)
                wizard_triggered = validate_picking(picking)

                _logger.info(
                    "Picking %s FINAL state: %s (wizard: %s) (tracking assigned: %s)",
                    picking.name, picking.state, wizard_triggered, gets_tracking_ref
                )

                results[picking.id] = {
                    'picking_id': picking.id,
                    'picking_name': picking.name,
                    'state': picking.state,
                    'wizard_triggered': wizard_triggered,
                    'has_extra_qty': gets_tracking_ref,
                    'carrier_tracking_ref': picking.carrier_tracking_ref,
                    'moves': move_debug,
                }
                return True

            # ---- KEY CHANGE: sirf is_backorder=True wali pickings process
            #      karo. Normal (is_backorder=False) Pick/Out pickings ko
            #      bilkul chhuo mat - unka apna standard Odoo flow chalega. ----
            pickings = order.picking_ids.sudo().filtered(lambda p: p.is_backorder)
            pickings = pickings.sorted(
                key=lambda p: (p.picking_type_id.sequence or 0, p.id)
            )

            # ---- Pass 1: process in route order ----
            for picking in pickings:
                handle_picking(picking)

            # ---- Pass 2: retry any picking that was 'waiting' in pass 1 but may now be
            #       'assigned' (because an earlier picking got unblocked/validated in
            #       pass 1) ----
            for picking in pickings:
                picking.invalidate_recordset()
                current = results.get(picking.id, {})
                if current.get('note') == 'waiting on previous operation':
                    handle_picking(picking)

            return {'status': 'success', 'pickings': list(results.values())}

        except Exception as e:
            import traceback
            _logger.error("update_delivery error: %s", traceback.format_exc())
            return {'status': 'error', 'message': str(e)}
