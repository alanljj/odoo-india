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

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from datetime import datetime
from openerp import netsvc

class stock_move(osv.osv):
    """
    This field used only for hide Serial split wizard after all moves goes into the work-order
    """
    _inherit = 'stock.move'

    def _return_history(self, cr, uid, ids, field_name, arg, context=None):
        """ Gets returns qty of picking
        """
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]
        return_history = {}.fromkeys(ids, 0.0)
        for m in self.browse(cr, uid, ids):
            if m.state == 'done':
                return_history[m.id] = 0
                for rec in m.move_history_ids2:
                    if rec.state == 'cancel': continue
                    # only take into account 'product return' moves, ignoring any other
                    # kind of upstream moves, such as internal procurements, etc.
                    # a valid return move will be the exact opposite of ours:
                    #     (src location, dest location) <=> (dest location, src location))
                    if rec.location_dest_id.id == m.location_id.id \
                        and rec.location_id.id == m.location_dest_id.id:
                        return_history[m.id] += (rec.product_qty * rec.product_uom.factor)
                # TODO:bettter to move in funct_inv
                if return_history[m.id] + m.qc_ok_qty == m.product_qty:
                    m.write({'qc_completed': True})
        return return_history

    def get_return_history(self, cr, uid, pick_id, context=None):
        """
            get return history
        """
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, pick_id, context=context)
        return_history = {}
        for m  in pick.move_lines:
            if m.state == 'done':
                return_history[m.id] = 0
                for rec in m.move_history_ids2:
                    # only take into account 'product return' moves, ignoring any other
                    # kind of upstream moves, such as internal procurements, etc.
                    # a valid return move will be the exact opposite of ours:
                    #     (src location, dest location) <=> (dest location, src location))
                    if rec.location_dest_id.id == m.location_id.id \
                        and rec.location_id.id == m.location_dest_id.id:
                        return_history[m.id] += (rec.product_qty * rec.product_uom.factor)
        return return_history

    # TODO : Better idea to called funct_inv and write to move
#    def _set_qc_completed(self, cr, uid, id, name, value, args, context=None):
#        """ 
#        -process
#            Calculates returned_qty + qc_qty == total qty
#                then
#                    qc_completed field Mark as true
#        """
#        if not value:
#            return False
#        return True

    _columns = {
        'moves_to_workorder': fields.boolean('Raw Material Move To Work-Center?'),
        # This field used for add raw materials dynamicaly on production order
        'extra_consumed': fields.boolean('Extra Consumed ?', help="Extra consumed raw material on production order"),
        'picking_qc_id': fields.many2one('stock.picking', 'QC Picking'),
        'qc_approved': fields.boolean('QC Approved?'),
        'qc_completed': fields.boolean('QC Completed?'),
        'qc_ok_qty': fields.float('QC Qty ', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'qc_rejected_qty': fields.float('Rejected Qty ', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),

        'purchase_qty': fields.float('Purchase Qty', digits_compute=dp.get_precision('Product Unit of Measure')),
        'purchase_uom_id': fields.many2one('product.uom', 'Purchase UoM'),

        'srvc_ordr_qty': fields.float('Deliver Qty ', digits_compute=dp.get_precision('Product Unit of Measure')),
        'srvc_ordr_uom': fields.many2one('product.uom', 'Deliver UoM'),
        'qc_ok_qty': fields.float('QC Qty ', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),

        'is_qc': fields.boolean('Can be QC?'),
        'returned_qty': fields.function(_return_history, method=True,string="Return Qty", digits_compute=dp.get_precision('Product Unit of Measure')),

        #Fields here overwrites only for readonly process.
        'date': fields.datetime('Move Done Date', states={'done': [('readonly', True)]}, required=True, select=True, help="Move date: scheduled date until move is done, then date of actual move processing"),
        'date_expected': fields.datetime('Expected Date', states={'done': [('readonly', True)]},required=True, help="Scheduled date for the processing of this move"),
        'received_date': fields.datetime('Received Date',states={'done': [('readonly', True)]}),
        'qc_approved_date': fields.datetime('QC Approved Date',states={'done': [('readonly', True)]}),

#        'product_id': fields.many2one('product.product', 'Product', required=True, select=True, domain=[('type','<>','service')],readonly=True, states={'draft': [('readonly', False)]}),
#        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
#            required=True,readonly=True, states={'draft': [('readonly', False)]},
#            help="This is the quantity of products from an inventory "
#                "point of view. For moves in the state 'done', this is the "
#                "quantity of products that were actually moved. For other "
#                "moves, this is the quantity of product that is planned to "
#                "be moved. Lowering this quantity does not generate a "
#                "backorder. Changing this quantity on assigned moves affects "
#                "the product reservation, and should be done with care."
#        ),
#        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly=True, states={'draft': [('readonly', False)]}),
#        'product_uos_qty': fields.float('Quantity (UOS)', digits_compute=dp.get_precision('Product Unit of Measure'),readonly=True, states={'draft': [('readonly', False)]}),
#        'product_uos': fields.many2one('product.uom', 'Product UOS',readonly=True, states={'draft': [('readonly', False)]}),
#        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True,readonly=True, states={'draft': [('readonly', False)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
#        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True,readonly=True, states={'draft': [('readonly', False)]}, select=True, help="Location where the system will stock the finished products."),
#        'partner_id': fields.many2one('res.partner', 'Destination Address ',readonly=True, states={'draft': [('readonly', False)]}, help="Optional address where goods are to be delivered, specifically used for allotment"),
#        'type': fields.related('picking_id', 'type', type='selection', selection=[('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal')], string='Shipping Type',readonly=True, states={'draft': [('readonly', False)]}),
#        'picking_id': fields.many2one('stock.picking', 'Reference', select=True,readonly=True, states={'draft': [('readonly', False)]}),
#        'origin': fields.related('picking_id','origin',type='char', size=64, relation="stock.picking", string="Source", store=True,readonly=True, states={'draft': [('readonly', False)]}),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        is_qc = self.browse(cr, uid, id, context=context).is_qc
        if context and context.get('split_move',False): is_qc = True
        default.update({'qc_completed': False, 'qc_ok_qty':0.0,'is_qc':is_qc,'extra_consumed':False,'received_date':False})
        return super(stock_move, self).copy(cr, uid, id, default, context=context)

    def _prepare_chained_picking(self, cr, uid, picking_name, picking, picking_type, moves_todo, context=None):
        """Prepare the definition (values) to create a new chained picking.

           :param str picking_name: desired new picking name
           :param browse_record picking: source picking (being chained to)
           :param str picking_type: desired new picking type
           :param list moves_todo: specification of the stock moves to be later included in this
               picking, in the form::

                   [[move, (dest_location, auto_packing, chained_delay, chained_journal,
                                  chained_company_id, chained_picking_type)],
                    ...
                   ]

               See also :meth:`stock_location.chained_location_get`.
        -Our Process
            - To attach purchase order with in type chain location
        """
        res = super(stock_move, self)._prepare_chained_picking(cr, uid, picking_name, picking, picking_type, moves_todo, context=context)
        if picking_type == 'internal':
            if picking.purchase_id:
                res.update({'purchase_id': picking.purchase_id.id})
        return res

    def action_process_qc2x(self, cr, uid, ids, context=None):
        """
        -Process
            Call wizard for quality control to next "x"(purchase order destination location) location
        """
        context = context or {}
        data = self.browse(cr, uid, ids[0])
        if not (data.picking_id and data.picking_id.purchase_id):
            raise osv.except_osv(_('Warning!'), _('You cannot process this move to transfer another location')) 
        context.update({'product_id':data.product_id.id, 'to_qc_qty': data.product_qty - (data.qc_ok_qty + data.qc_rejected_qty) , 
                        'qc_ok_qty':data.qc_ok_qty, 'qc_rejected_qty': data.qc_rejected_qty})
        return {
                'name': 'Transfer Quantity from QC to X location',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'qc2xlocation',
                'type': 'ir.actions.act_window',
                'target':'new',
                'context':context
                }

    def action_process_qc2reject(self, cr, uid, ids, context=None):
        """
        -Process
            Call wizard for rejection quantity of product
        """
        context = context or {}
        data = self.browse(cr, uid, ids[0])
        if not (data.picking_id and data.picking_id.purchase_id):
            raise osv.except_osv(_('Warning!'), _('You cannot process this move for rejection quantity')) 
        context.update({'product_id':data.product_id.id, 'to_qc_qty': data.product_qty - (data.qc_ok_qty+data.qc_rejected_qty), 'qc_ok_qty':data.qc_ok_qty, 'already_rejected_qty': data.qc_rejected_qty})
        return {
                'name': 'QC Rejection Process',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'qc2reject',
                'type': 'ir.actions.act_window',
                'target':'new',
                'context':context
                }

    def action_done(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        @return:
        """
        picking_ids = []
        move_ids = []
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}

        todo = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state=="draft":
                todo.append(move.id)
        if todo:
            self.action_confirm(cr, uid, todo, context=context)
            todo = []

        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done','cancel']:
                continue
            move_ids.append(move.id)

            if move.picking_id:
                picking_ids.append(move.picking_id.id)
            if move.move_dest_id.id and (move.state != 'done'):
                # Downstream move should only be triggered if this move is the last pending upstream move
                other_upstream_move_ids = self.search(cr, uid, [('id','!=',move.id),('state','not in',['done','cancel']),
                                            ('move_dest_id','=',move.move_dest_id.id)], context=context)
                if not other_upstream_move_ids:
                    self.write(cr, uid, [move.id], {'move_history_ids': [(4, move.move_dest_id.id)]})
                    if move.move_dest_id.state in ('waiting', 'confirmed'):
                        self.force_assign(cr, uid, [move.move_dest_id.id], context=context)
                        if move.move_dest_id.picking_id:
                            wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                        if move.move_dest_id.auto_validate:
                            self.action_done(cr, uid, [move.move_dest_id.id], context=context)

            self._create_product_valuation_moves(cr, uid, move, context=context)
            if move.state not in ('confirmed','done','assigned'):
                todo.append(move.id)

        if todo:
            self.action_confirm(cr, uid, todo, context=context)

        #Just to update move Received Date
        self.write(cr, uid, move_ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),'received_date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        for id in move_ids:
            wf_service.trg_trigger(uid, 'stock.move', id, cr)

        for pick_id in picking_ids:
            wf_service.trg_write(uid, 'stock.picking', pick_id, cr)

        return True

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial pickings and moves done.
        @param partial_datas: Dictionary containing details of partial picking
                          like partner_id, delivery_date, delivery
                          moves with product_id, product_qty, uom
        """
        res = {}
        picking_obj = self.pool.get('stock.picking')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        wf_service = netsvc.LocalService("workflow")

        if context is None:
            context = {}

        complete, too_many, too_few = [], [], []
        move_product_qty = {}
        prodlot_ids = {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ('done', 'cancel'):
                continue
            partial_data = partial_datas.get('move%s'%(move.id), False)
            assert partial_data, _('Missing partial picking data for move #%s.') % (move.id)
            product_qty = partial_data.get('product_qty',0.0)
            move_product_qty[move.id] = product_qty
            product_uom = partial_data.get('product_uom',False)
            product_price = partial_data.get('product_price',0.0)
            product_currency = partial_data.get('product_currency',False)
            prodlot_ids[move.id] = partial_data.get('prodlot_id')
            if move.product_qty == product_qty:
                complete.append(move)
            elif move.product_qty > product_qty:
                too_few.append(move)
            else:
                raise osv.except_osv(_('Over Limit!'), _('You cannot allow more then PO Qty.'))

            # Average price computation
            if (move.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
                product = product_obj.browse(cr, uid, move.product_id.id)
                move_currency_id = move.company_id.currency_id.id
                context['currency_id'] = move_currency_id
                qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)
                if qty > 0:
                    new_price = currency_obj.compute(cr, uid, product_currency,
                            move_currency_id, product_price, round=False)
                    new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                            product.uom_id.id)
                    if product.qty_available <= 0:
                        new_std_price = new_price
                    else:
                        # Get the standard price
                        amount_unit = product.price_get('standard_price', context=context)[product.id]
                        new_std_price = ((amount_unit * product.qty_available)\
                            + (new_price * qty))/(product.qty_available + qty)

                    product_obj.write(cr, uid, [product.id],{'standard_price': new_std_price})

                    # Record the values that were chosen in the wizard, so they can be
                    # used for inventory valuation if real-time valuation is enabled.
                    self.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency,
                                })

        for move in too_few:
            product_qty = move_product_qty[move.id]
            if product_qty != 0:
                defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty,
                            'picking_id' : move.picking_id.id,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            }
                prodlot_id = prodlot_ids[move.id]
                if prodlot_id:
                    defaults.update(prodlot_id=prodlot_id)
                new_move = self.copy(cr, uid, move.id, defaults)
                complete.append(self.browse(cr, uid, new_move))
            self.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty - product_qty,
                        'product_uos_qty': move.product_qty - product_qty,
                        'prodlot_id': False,
                        'tracking_id': False,
                    })


        for move in too_many:
            self.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty,
                        'product_uos_qty': move.product_qty,
                    })
            complete.append(move)

        for move in complete:
            if prodlot_ids.get(move.id):
                self.write(cr, uid, [move.id],{'prodlot_id': prodlot_ids.get(move.id)})
            self.action_done(cr, uid, [move.id], context=context)
            if  move.picking_id.id :
                # TOCHECK : Done picking if all moves are done
                cr.execute("""
                    SELECT move.id FROM stock_picking pick
                    RIGHT JOIN stock_move move ON move.picking_id = pick.id AND move.state = %s
                    WHERE pick.id = %s""",
                            ('done', move.picking_id.id))
                res = cr.fetchall()
                if len(res) == len(move.picking_id.move_lines):
                    picking_obj.action_move(cr, uid, [move.picking_id.id])
                    wf_service.trg_validate(uid, 'stock.picking', move.picking_id.id, 'button_done', cr)

        return [move.id for move in complete]

stock_move()


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        picking_obj = self.browse(cr, uid, id, context=context)
        default = {
                   'move_lines_qc2store':False,
                   'total_moves_to_xloc':False,
                   #'pass_to_qc':False,
                   'qc_loc_id':False,
                   'move_loc_id':False,
                   'service_order':False,
                   'workorder_id':False,
                   'move_lines':[]
                   }
        return super(stock_picking, self).copy(cr, uid, id, default, context)

    def _get_picking(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[line.picking_id.id] = True
        return result.keys()

    def _total_moves_to_store(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'total_moves_to_xloc': False,
            }
            if len(order.move_lines) and (len(order.move_lines) == len([x.id for x in order.move_lines if x.qc_completed])):
                res[order.id] = {
                    'total_moves_to_xloc': True,
                }
        return res

    _columns = {
        'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', readonly=True, states={'draft': [('readonly', False)]}),
        'service_order': fields.boolean('Service Order'),
        'pass_to_qc': fields.boolean('QC Test?'),
        'dc_number': fields.char('DC Number',size=256),
        'dc_date': fields.date('DC Date'),
        'received_date': fields.datetime('Received Date'),
        'workorder_id':  fields.many2one('mrp.production.workcenter.line', 'Work-Order'),
        'move_lines_qc2store': fields.one2many('stock.move', 'picking_qc_id', 'Store Moves', readonly=True),
        'qc_loc_id': fields.many2one('stock.location', 'QC Location', readonly=True),
        'move_loc_id': fields.many2one('stock.location', 'Destination Location', readonly=True),
        'total_moves_to_xloc': fields.function(_total_moves_to_store, digits_compute=dp.get_precision('Account'), string='Total qty moves to x location?', type="boolean",
            store={
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 10),
                'stock.move': (_get_picking, ['qc_completed'], 10),
            },
            ),

        #Dates Commitments
        'ex_work_date': fields.date('Ex.work Delivery Date', help = "Date should be consider as date of Goods ready for delivery"),
        'shipping_time':  fields.integer('Shipping Time(In Days)'),
        'destination_date': fields.date('Destination  Delivery Date', help="Reaching date of delivery goods(Ex.work Delivery Date + Shipping Time)"),
    }

    def onchange_shipping_time(self, cr, uid, ids, ex_work_date, shipping_time, context=None):
        return {'value':{'destination_date':(datetime.strptime(ex_work_date, '%Y-%m-%d') + relativedelta(days=shipping_time)).strftime('%Y-%m-%d')}}

    _defaults = {
        'ex_work_date': fields.date.context_today,
        'shipping_time': 7,
    }

    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        res = super(stock_picking, self)._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
        res.update({'comment':''})
        if picking.sale_id:
            res.update({
                    'do_id': picking.id,
                    'do_address_id': picking.partner_id.id,
                    'so_date': picking.sale_id.date_order,
                    'do_name': picking.name,
                    'do_delivery_date': picking.ex_work_date,
                    'so_id': picking.sale_id.id,

                    'package_and_forwording':picking.sale_id.package_and_forwording, 
                    'insurance':picking.sale_id.insurance,
                    'freight':picking.sale_id.freight,
                    'extra_charges':picking.sale_id.extra_charges,
                    'round_off':picking.sale_id.round_off,

                })
        if picking.purchase_id:
            res.update({
                    'reference': picking.name,
                })
        return res

    def action_done(self, cr, uid, ids, context=None):
        """Changes picking state to done.
        
        This method is called at the end of the workflow by the activity "done".
        @return: True
        """
        # Just update recieved date at d end of received.
        self.write(cr, uid, ids, {'state': 'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S'),'received_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True


    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                product_currency = partial_data.get('product_currency',False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    raise osv.except_osv(_('Over Limit!'), _('You cannot allow more then PO Qty.'))

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id not in product_avail:
                        # keep track of stock on hand including processed lines not yet marked as done
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                move_currency_id, product_price, round=False)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                product.uom_id.id)
                        if product_avail[product.id] <= 0:
                            product_avail[product.id] = 0
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])\
                                + (new_price * qty))/(product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency})

                        product_avail[product.id] += qty



            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], 
                               {'name': sequence_obj.get(cr, uid,
                                            'stock.picking.%s'%(pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                            })
                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = pick.id
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, new_picking, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

stock_picking()

class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'
    _columns = {
        'service_order': fields.boolean('Service Order'),
        'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', readonly=True, states={'draft': [('readonly', False)]}),
        'workorder_id':  fields.many2one('mrp.production.workcenter.line', 'Work-Order'),

        #Dates Commitments
        'ex_work_date': fields.date('Ex.work Delivery Date', help = "Date should be consider as date of Goods ready for delivery"),
        'shipping_time':  fields.integer('Shipping Time(In Days)'),
        'destination_date': fields.date('Destination  Delivery Date', help="Reaching date of delivery goods(Ex.work Delivery Date + Shipping Time)"),
    }

    def onchange_shipping_time(self, cr, uid, ids, ex_work_date, shipping_time, context=None):
        return {'value':{'destination_date':(datetime.strptime(ex_work_date, '%Y-%m-%d') + relativedelta(days=shipping_time)).strftime('%Y-%m-%d')}}

    _defaults = {
        'ex_work_date': fields.date.context_today,
        'shipping_time': 7,
    }
stock_picking_out()

class stock_picking_in(osv.osv):
    _inherit = 'stock.picking.in'

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        picking_obj = self.browse(cr, uid, id, context=context)
        default = {
                   'move_lines_qc2store':False,
                   'total_moves_to_xloc':False,
                   'pass_to_qc':False,
                   'qc_loc_id':False,
                   'move_loc_id':False,
                   'service_order':False,
                   'workorder_id':False,
                   'move_lines':[],
                   'purchase_id':False
                   }
        return super(stock_picking_in, self).copy(cr, uid, id, default, context)

    def _get_picking(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[line.picking_id.id] = True
        return result.keys()

    def _total_moves_to_store(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'total_moves_to_xloc': False,
            }
            if len(order.move_lines) and (len(order.move_lines) == len([x.id for x in order.move_lines if x.qc_completed])):
                res[order.id] = {
                    'total_moves_to_xloc': True,
                }
        return res

    _columns = {
        'pass_to_qc': fields.boolean('QC Test?'),
        'dc_number': fields.char('DC Number',size=256),
        'dc_date': fields.date('DC Date'),
        'received_date': fields.datetime('Received Date'),
        'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves',readonly=True, states={'draft': [('readonly', False)]}),
        'move_lines_qc2store': fields.one2many('stock.move', 'picking_qc_id', 'Store Moves', readonly=True),
        'qc_loc_id': fields.many2one('stock.location', 'QC Location', readonly=True),
        'move_loc_id': fields.many2one('stock.location', 'Destination Location', readonly=True),
        'total_moves_to_xloc': fields.function(_total_moves_to_store, digits_compute=dp.get_precision('Account'), string='Total qty moves to x location?', type="boolean",
            store={
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 10),
                'stock.move': (_get_picking, ['qc_completed'], 10),
            },
            ),
        
    }
stock_picking_in()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
