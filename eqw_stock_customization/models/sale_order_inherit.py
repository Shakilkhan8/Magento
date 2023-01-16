from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    installer_id = fields.Many2one('res.users', string="Installer")

    def action_confirm(self):
        """
        This method inherited for identify the Magento order and pass the context
        to manage the BOM.
        :return: super call.
        """
        res = super(SaleOrder, self).action_confirm()
        for rec in self:
            rec.send_products_to_installer()
        return res

    def send_products_to_installer(self):
        """
        Send Email  products
        :param warehouse:
        :return:
        """
        for rec in self:
            email_users = [rec.installer_id.email]
            mail_content = "Dear Sir, <br/> Products that need to install  <br/>"
            mail_content += "<strong>Customer Details </strong><br/>"
            mail_content += " - Name Customer: %s<br/> " % (rec.partner_id.name)
            mail_content += " - Address : %s,%s,%s,%s,%s<br/> " % (
            rec.partner_id.street, rec.partner_id.street2, rec.partner_id.city, rec.partner_id.state_id.display_name,
            rec.partner_id.country_id.name)
            mail_content += "<strong>Deadline : %s </strong><br/>" % (rec.expected_date)
            mail_content += "<strong>Products: </strong><br/>"
            need_to_install = False
            for line in rec.order_line:
                if line.display_type == "line_note":
                    need_to_install = True
                    mail_content += "  %s  <br/>" % (line.name)
            if need_to_install:
                if not rec.installer_id:
                    raise ValidationError(_(" Please add the  installer to send  email."))
                send_notif = self.env['mail.mail'].sudo().create({
                    'subject': _('New Order %s ') % (rec.origin),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_users and ', '.join(email_users) or False,
                })
                print("send_notif ===>>", send_notif)
                send_notif.send()
