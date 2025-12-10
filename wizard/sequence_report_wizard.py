import base64
import io
import csv
from odoo import models, fields, api, _

class TagSequenceReportColumn(models.TransientModel):
    _name = 'tag.sequence.report.column'
    _description = 'Configuración de Columnas del Informe'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('tag.sequence.report.wizard', string='Wizard', ondelete='cascade')
    sequence = fields.Integer(string='Orden', default=10)

    # Campo interno (técnico) vs Etiqueta (lo que sale en el CSV)
    field_name = fields.Selection([
        ('code', 'Código Interno'),
        ('name', 'Nombre Secuencia'),
        ('value', 'Valor Calculado'),
        ('measure_type', 'Tipo de Medida'),
        ('tags_used', 'Etiquetas')
    ], string='Dato', required=True, readonly=True)

    label = fields.Char(string='Título Columna CSV', required=True)
    active = fields.Boolean(string='Incluir en CSV', default=True)

class TagSequenceReportLine(models.TransientModel):
    _name = 'tag.sequence.report.line'
    _description = 'Línea de Previsualización del Informe'

    wizard_id = fields.Many2one('tag.sequence.report.wizard', string='Wizard', ondelete='cascade')

    code = fields.Char(string='Código')
    name = fields.Char(string='Nombre')
    value = fields.Float(string='Valor (Positivo)')
    measure_type = fields.Selection(
        [('balance', 'Importe'), ('quantity', 'Unidades')], 
        string='Tipo'
    )
    tags_used = fields.Char(string='Etiquetas')

class TagSequenceReportWizard(models.TransientModel):
    _name = 'tag.sequence.report.wizard'
    _description = 'Asistente Informe CSV de Secuencias'

    state = fields.Selection([
        ('draft', 'Selección'), 
        ('preview', 'Previsualización'),
        ('done', 'Hecho')
    ], default='draft', string='Estado')

    collection_id = fields.Many2one('tag.sequence.collection', string='Colección', required=True)
    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)

    line_ids = fields.One2many('tag.sequence.report.line', 'wizard_id', string='Líneas del Informe')
    column_ids = fields.One2many('tag.sequence.report.column', 'wizard_id', string='Configuración Columnas')

    csv_file = fields.Binary(string='Archivo CSV', readonly=True)
    csv_filename = fields.Char(string='Nombre Archivo', readonly=True)

    def _get_default_columns(self):
        return [
            {'field_name': 'code', 'label': 'Código', 'sequence': 10},
            {'field_name': 'name', 'label': 'Nombre', 'sequence': 20},
            {'field_name': 'value', 'label': 'Valor (Positivo)', 'sequence': 30},
            {'field_name': 'measure_type', 'label': 'Tipo', 'sequence': 40},
            {'field_name': 'tags_used', 'label': 'Etiquetas Usadas', 'sequence': 50},
        ]

    def action_calculate_preview(self):
        # 1. Limpiar líneas anteriores
        self.line_ids.unlink()

        # 2. Inicializar columnas si no existen (solo la primera vez)
        if not self.column_ids:
            cols = []
            for c in self._get_default_columns():
                c['wizard_id'] = self.id
                cols.append(c)
            self.env['tag.sequence.report.column'].create(cols)

        # 3. Buscar items y calcular
        items = self.env['tag.sequence.item'].search([
            ('collection_id', '=', self.collection_id.id)
        ])

        new_lines = []
        for item in items:
            if not item.analytic_tag_ids:
                final_value = 0.0
                tags_str = ""
            else:
                domain = [
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('parent_state', '=', 'posted'), 
                ]

                for tag in item.analytic_tag_ids:
                    domain.append(('analytic_tag_ids', '=', tag.id))

                account_lines = self.env['account.move.line'].search(domain)

                if item.measure_type == 'quantity':
                    raw_value = sum(line.quantity for line in account_lines)
                else:
                    raw_value = sum(line.balance for line in account_lines)

                final_value = abs(raw_value)
                tags_str = ", ".join(item.analytic_tag_ids.mapped('name'))

            new_lines.append({
                'wizard_id': self.id,
                'code': item.code,
                'name': item.name,
                'value': final_value,
                'measure_type': item.measure_type,
                'tags_used': tags_str
            })

        if new_lines:
            self.env['tag.sequence.report.line'].create(new_lines)

        self.write({'state': 'preview'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tag.sequence.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_reset(self):
        # Mantenemos las columnas personalizadas, solo borramos datos
        self.write({'state': 'draft', 'line_ids': [(5, 0, 0)]}) 
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tag.sequence.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_csv(self):
        self.ensure_one()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # 1. Obtener columnas activas y ordenadas
        active_columns = self.column_ids.filtered(lambda c: c.active).sorted('sequence')

        # 2. Escribir Cabecera (Usando el 'label' personalizado)
        writer.writerow(active_columns.mapped('label'))

        # 3. Escribir Datos Dinámicamente
        for line in self.line_ids:
            row = []
            for col in active_columns:
                # Obtenemos el valor bruto del campo
                val = getattr(line, col.field_name)

                # Formateo específico según el campo
                if col.field_name == 'value':
                    val = f"{val:.2f}"
                elif col.field_name == 'measure_type':
                    val = 'Unidades' if val == 'quantity' else 'Importe'

                row.append(val)
            writer.writerow(row)

        csv_content = output.getvalue().encode('utf-8')
        output.close()

        self.csv_file = base64.b64encode(csv_content)
        self.csv_filename = f"Informe_{self.collection_id.name}_{self.date_from}.csv"

        self.write({'state': 'done'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tag.sequence.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }