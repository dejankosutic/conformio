# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from random import randint, seed
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from openerp import models, api, tools, fields
from openerp.modules.module import get_module_resource


class UserAvatarInitials(models.Model):
    _inherit = "res.users"

    _defaults = {
        'image': False,
    }

    use_initials_avatar = fields.Boolean(string="Use Initials Avatar")

    @api.model
    def create(self, vals=None):
        """ Use avatar initials as default image
        """
        vals['use_initials_avatar'] = False
        if not vals.get('image'):
            _name = vals.get('name', False) and vals['name'] or ''
            _firstname = vals.get('firstname', False) and vals['firstname'] or ''
            _lastname = vals.get('lastname', False) and vals['lastname'] or ''

            avatar_text = _name or _firstname + ' ' + _lastname
            image = self._get_avatar(128, avatar_text, "PNG")
            vals['image'] = tools.image_resize_image_big(
                image.encode('base64'))
            vals['use_initials_avatar'] = True
        return super(UserAvatarInitials, self).create(vals)

    @api.multi
    def write(self, vals=None):
        """ Use avatar initials as default image
        """
        if 'image' in vals:
            if vals.get('image'):
                vals['use_initials_avatar'] = False
            else:
                vals['use_initials_avatar'] = True
        if vals.get('use_initials_avatar', self.use_initials_avatar):
            avatar_text = vals.get('name', False) or \
                str(vals.get('firstname', self.firstname or '')) + ' ' + \
                str(vals.get('lastname', self.lastname or ''))
            image = self._get_avatar(128, avatar_text, "PNG")
            vals['image'] = tools.image_resize_image_big(
                image.encode('base64'))
            vals['use_initials_avatar'] = True
        return super(UserAvatarInitials, self).write(vals)

    def _get_avatar(self, size, text, filetype="JPEG"):
        """ Generates the avatar image
        """
        render_size = max(size, 512)
        seed(text)
        r, g, b = 255, 255, 255
        while r + g + b > 255 * 2:
            r = randint(0, 255)
            g = randint(0, 255)
            b = randint(0, 255)
        back_color = (r, g, b)
        new_image = Image.new('RGB', (render_size, render_size), back_color)
        draw = ImageDraw.Draw(new_image)
        path = get_module_resource('user_avatar_initials', 'static/font',
                                   'OpenSans-Regular.ttf')
        font = ImageFont.truetype(path, size=int(0.6 * render_size))
        text = text or " "
        initials = ''
        for word in text.split():
            if len(initials) < 2:
                initials = initials + word[0].upper()
        # determine text position
        width, height = font.getsize(initials)
        left = (render_size - width) / 2.0
        top = (render_size - height) / 5.5
        text_position = left, top

        draw.text(text_position,
                  initials,
                  fill=(255, 255, 255),  # white letters
                  font=font)
        stream = BytesIO()
        new_image = new_image.resize((size, size), Image.ANTIALIAS)
        new_image.save(stream, format=filetype, optimize=True)
        return stream.getvalue()
