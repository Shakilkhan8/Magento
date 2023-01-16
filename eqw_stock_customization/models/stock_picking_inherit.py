from odoo import models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def send_products_to_shipper(self):
        """
        Send Email  products
        :param warehouse:
        :return:
        """
        for rec in self:
            email_users = [rec.picking_type_id.warehouse_id.email]
            mail_content = "Dear Sir, <br/> There are Product in shipment <br/>"
            mail_content += "<strong>Customer Details </strong><br/>"
            mail_content += " - Name Customer: %s<br/> " % (rec.partner_id.name)
            mail_content += " - Phone & Mobile : %s,%s<br/> " % (rec.partner_id.phone, rec.partner_id.mobile)
            mail_content += " - Address : %s,%s,%s,%s,%s<br/> " % (
            rec.partner_id.street, rec.partner_id.street2, rec.partner_id.city, rec.partner_id.state_id.display_name,
            rec.partner_id.country_id.name)
            mail_content += "<strong>Deadline : %s </strong><br/>" % (rec.date_deadline)
            mail_content += "<strong>Products: </strong><br/>"
            for line in rec.move_ids_without_package:
                mail_content += " - The product  %s  with quantity( %s ) <br/>" % (line.product_id.display_name, str(line.product_uom_qty))
            send_notif = self.env['mail.mail'].sudo().create({
                'subject': _('New Order %s ') % (rec.origin),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_users and ', '.join(email_users) or False,
            })
            print("send_notif ===>>", send_notif)
            send_notif.send()
