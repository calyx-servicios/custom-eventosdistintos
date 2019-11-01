# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
import logging
from odoo.exceptions import ValidationError




_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
      

    @api.multi
    def _get_to_pay_move_lines_domain(self, move_id):
        self.ensure_one()
        account_internal_type = 'receivable'
        return [
            ('partner_id.commercial_partner_id', '=',
                self.id),
            ('account_id.internal_type', '=',
                account_internal_type),
            ('account_id.reconcile', '=', True),
            ('reconciled', '=', False),
            ('full_reconcile_id', '=', False),
            ('move_id', '=', move_id),
            ('company_id', '=', self.company_id.id),
            
        ]

    @api.multi
    def get_account_status(self):
        self.ensure_one()
        invoices =[] 
        currency = self.env.user.company_id.currency_id
        today=fields.Date.context_today(self)
        amount_invoiced=0.0
        amount_overdue=0.0
        amount_payed=0.0
        amount_residual=0.0

        for partner in self:
            invoices_list = self.env['account.invoice'].search([('partner_id','=',partner.id),('state','=','open')])
            for invoice in invoices_list:
                debt_lines ={}
                _filter_lines=partner._get_to_pay_move_lines_domain(invoice.move_id.id)
                invoice_amount=0.0
                invoice_payed=0.0
                invoice_percentage=0.0
                invoice_overdue=0.0
                lines = self.env['account.move.line'].search(_filter_lines)
                for line in lines:
                    key = (line)
                    overdue = 0.0
                    payed=round(line.balance-line.amount_residual,2)
                    percentage=round(100*(payed/line.balance),2)
                    amount_residual+=line.amount_residual
                    amount_invoiced+=line.balance
                    amount_payed+=payed
                    invoice_amount+=line.balance
                    invoice_payed+=payed
                    
                    if line.date_maturity < today and line.amount_residual:
                        amount_overdue+=line.amount_residual
                        overdue=round(line.amount_residual,2)
                        invoice_overdue+=overdue
                    debt_lines[key] = {'payed':payed,'percentage':percentage,'overdue':overdue}
                    
                
                _debt_lines= sorted([{
                    'date': line.date,
                    'date_maturity': line.date_maturity,
                    'overdue': info['overdue'],
                    'move': line.move_id.name,
                    'invoice': line.invoice_id.name,
                    'balance': line.balance,
                    'amount_residual': line.amount_residual,
                    'payment_amount': info['payed'],
                    'percentage': info['percentage'],
                    'currency_id': line.currency_id.id
                } for (line), info in debt_lines.items()],key=lambda l: l['date_maturity'])
                invoice_percentage=round(100*(invoice_payed/invoice_amount),2)
                invoice_payed=round(invoice_payed,2)
                invoice_overdue=round(invoice_overdue,2)
                invoices.append({
                    'name': invoice.display_name,
                    'date': invoice.date,
                    'amount': invoice.amount_total,
                    'percentage': invoice_percentage,
                    'payed': invoice_payed,
                    'overdue': invoice_overdue,
                    'residual': invoice.residual,
                    'debt_lines': _debt_lines
                })
        data = {
            'amount_invoiced':round(amount_invoiced,2),
            'amount_overdue':round(amount_overdue,2),
            'amount_payed':round(amount_payed,2),
            'amount_residual':round(amount_residual,2),
            'invoices':invoices
        }
        return data