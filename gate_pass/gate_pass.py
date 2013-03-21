# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.osv import fields, osv

class stock_picking(osv.Model):
    _inherit = 'stock.picking'

    _columns = {
        'series':fields.selection([('repair', 'Repair'), ('purchase', 'Purchase'), ('store', 'Store')], 'Series'),
        'type':fields.selection([('foc', 'Free Of Cost'), ('chargeable', 'Chargeable'), ('sample', 'Sample'), ('contract', 'Contract'), ('cash', 'Cash'), ('Loan', 'Loan')], 'Type'),
    }

stock_picking()

class gate_pass(osv.Model):
    _name = 'gate.pass'
    _description = 'Gate Pass'

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'gate_pass_no': fields.char('Gate Pass No', size=256, required=True),
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        'series':fields.related('picking_id', 'series', type='selection', string='Series', store=True),
        'type':fields.related('picking_id', 'type', type='selection', string='Type', store=True),
        'date': fields.datetime('Gate Pass Date', required=True),
        'partner_id':fields.many2one('res.partner', 'Supplier', required=True),
        'department_id': fields.many2one('stock.location', 'Department', required=True),
        'indent_id': fields.many2one('indent.indent', 'Indent'),
        'move_lines': fields.one2many('stock.move', 'gate_pass_id', 'Products'),
        'description': fields.text('Remarks'),
    }

    def _default_stock_location(self, cr, uid, context=None):
        stock_location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock')
        return stock_location.id

    _defaults = {
        'gate_pass_no': lambda obj, cr, uid, context:obj.pool.get('ir.sequence').get(cr, uid, 'gate.pass'),
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'series': 'repair',
        'type': 'foc',
        'department_id': _default_stock_location,
    }

gate_pass()

class stock_move(osv.Model):
    _inherit = 'stock.move'

    _columns = {
        'gate_pass_id': fields.many2one('gate.pass', 'Gate Pass', required=True, ondelete='cascade'),
    }

stock_move()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: