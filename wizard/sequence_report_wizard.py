import base64
import io
import csv
from odoo import models, fields, api, _

class TagSequenceReportWizard(models.TransientModel):
    _name = 'tag.sequence.report.wizard'
    _description = 'Asistente Informe CSV de Secuencias'

    collection_id = fields.Many2one('tag.sequence.collection', string='Colección', required=True)
    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)

    csv_file = fields.Binary(string='Archivo CSV', readonly=True)
    csv_filename = fields.Char(string='Nombre Archivo', readonly=True)

    def action_generate_csv(self):
        self.ensure_one()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Cabecera actualizada
        writer.writerow(['Código', 'Nombre', 'Valor (Positivo)', 'Tipo', 'Etiquetas Usadas'])

        items = self.env['tag.sequence.item'].search([
            ('collection_id', '=', self.collection_id.id)
        ])

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

                # Filtro AND para las etiquetas
                for tag in item.analytic_tag_ids:
                    domain.append(('analytic_tag_ids', '=', tag.id))

                lines = self.env['account.move.line'].search(domain)

                # LOGICA DE MEDIDA Y VALOR ABSOLUTO
                if item.measure_type == 'quantity':
                    # Sumamos Unidades (quantity)
                    raw_value = sum(line.quantity for line in lines)
                else:
                    # Sumamos Dinero (balance)
                    raw_value = sum(line.balance for line in lines)

                # Convertimos siempre a positivo
                final_value = abs(raw_value)

                tags_str = ", ".join(item.analytic_tag_ids.mapped('name'))

            # Escribimos la fila con el nuevo formato
            writer.writerow([
                item.code, 
                item.name, 
                f"{final_value:.2f}", 
                'Unidades' if item.measure_type == 'quantity' else 'Importe',
                tags_str
            ])

        csv_content = output.getvalue().encode('utf-8')
        output.close()

        self.csv_file = base64.b64encode(csv_content)
        self.csv_filename = f"Informe_{self.collection_id.name}_{self.date_from}.csv"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tag.sequence.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }