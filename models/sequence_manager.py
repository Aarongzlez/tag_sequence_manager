from odoo import models, fields, api

class TagSequenceItem(models.Model):
    _name = 'tag.sequence.item'
    _description = 'Elemento de Secuencia'
    _rec_name = 'code'
    _order = 'code'

    collection_id = fields.Many2one('tag.sequence.collection', string='Colección', required=True, ondelete='cascade')

    code = fields.Char(string='Código', required=True, index=True)
    name = fields.Char(string='Nombre', required=True)

    analytic_tag_ids = fields.Many2many(
        comodel_name='account.analytic.tag',
        string='Secuencia de Etiquetado'
    )

    # NUEVO CAMPO: Tipo de medida (Dinero vs Unidades)
    measure_type = fields.Selection(
        [('balance', 'Importe Monetario'), ('quantity', 'Unidades (Cantidad)')],
        string='Tipo de Medida',
        default='balance',
        required=True,
        help="Define si esta secuencia debe sumar el saldo contable o la cantidad de unidades."
    )

    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('code_collection_uniq', 'unique (code, collection_id)', 'El código debe ser único dentro de la misma colección.')
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}"

class TagSequenceCollection(models.Model):
    _name = 'tag.sequence.collection'
    _description = 'Colección de Secuencias'
    _order = 'name'

    name = fields.Char(string='Nombre de Colección', required=True)
    description = fields.Text(string='Descripción')

    sequence_ids = fields.One2many('tag.sequence.item', 'collection_id', string='Secuencias')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre de la colección debe ser único.')
    ]