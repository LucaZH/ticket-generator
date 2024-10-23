from PIL import Image, ImageDraw, ImageFont
import qrcode
from PIL import ImageOps
from dataclasses import dataclass
from typing import Tuple
import os

@dataclass
class TicketConfig:
    width: int = 1202
    height: int = 450
    padding: int = 50
    font_large_size: int = 36
    font_small_size: int = 16
    icon_size: int = 24 

@dataclass
class EventDetails:
    title: str
    category: str
    date: str
    time: str
    location: str
    ticket_type: str
    url: str

@dataclass
class TicketData:
    ticket_number: int
    owner: str
    qr_data: str
    event: EventDetails

class TicketGenerator:
    def __init__(self, config: TicketConfig = TicketConfig(), icons_folder: str = "icons"):
        self.config = config
        self.icons_folder = icons_folder
        self.setup_fonts()
        self.load_icons()
        
    def setup_fonts(self):
        try:
            self.font_large = ImageFont.truetype("arial.ttf", self.config.font_large_size)
            self.font_small = ImageFont.truetype("arial.ttf", self.config.font_small_size)
            self.font_bold = ImageFont.truetype("arialbd.ttf", self.config.font_large_size)
        except IOError:
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_bold = ImageFont.load_default()

    def load_icons(self):
        self.icons = {}
        icon_files = {
            'calendar': 'calendar.png',
            'clock': 'clock.png',
            'map': 'map.png',
            'ticket': 'ticket.png'
        }
        
        for icon_name, file_name in icon_files.items():
            icon_path = os.path.join(self.icons_folder, file_name)
            try:
                icon = Image.open(icon_path).convert('RGBA')
                icon = icon.resize((self.config.icon_size, self.config.icon_size), Image.LANCZOS)
                self.icons[icon_name] = icon
            except Exception as e:
                print(f"Error loading icon {file_name}: {e}")
                self.icons[icon_name] = Image.new('RGBA', (self.config.icon_size, self.config.icon_size), (0, 0, 0, 0))

    def draw_icon_with_text(self, ticket: Image.Image, x: int, y: int, icon_type: str, text: str) -> None:
        draw = ImageDraw.Draw(ticket)
        icon = self.icons[icon_type]
        
        if 'A' in icon.getbands():
            ticket.paste(icon, (x, y), icon)
        else:
            ticket.paste(icon, (x, y))
            
        text_y = y + (self.config.icon_size - self.config.font_small_size) // 2
        draw.text((x + self.config.icon_size + 10, text_y), text, font=self.font_small, fill=(81, 79, 79))

    def create_rounded_rectangle(self, draw, coords, radius, fill):
        x1, y1, x2, y2 = coords
        draw.rectangle([x1+radius, y1, x2-radius, y2], fill=fill)
        draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill)
        draw.pieslice([x1, y1, x1+radius*2, y1+radius*2], 180, 270, fill=fill)
        draw.pieslice([x2-radius*2, y1, x2, y1+radius*2], 270, 360, fill=fill)
        draw.pieslice([x1, y2-radius*2, x1+radius*2, y2], 90, 180, fill=fill)
        draw.pieslice([x2-radius*2, y2-radius*2, x2, y2], 0, 90, fill=fill)

    def get_text_dimensions(self, draw, text: str, font) -> Tuple[int, int]:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def generate_ticket(self, background_path: str, ticket_data: TicketData):
        ticket = Image.new("RGB", (self.config.width, self.config.height), "white")
        background = self.process_background(background_path, ticket)
        ticket.paste(background, (0, 0))
        ticket = self.add_gradient(ticket)
        draw = ImageDraw.Draw(ticket)

        y_pos = 20
        draw.text((self.config.padding, y_pos), f"N: {ticket_data.ticket_number}", font=self.font_bold, fill=(0, 0, 0))
        
        y_pos = 70
        draw.text((self.config.padding, y_pos), f"Propriétaire: {ticket_data.owner}", font=self.font_small, fill=(0, 0, 0))

        y_pos = 130
        draw.text((self.config.padding, y_pos), "Informations", font=self.font_large, fill=(255, 215, 0))
        
        y_pos = 180
        title_text = ticket_data.event.title
        title_width, _ = self.get_text_dimensions(draw, title_text, self.font_bold)
        draw.text((self.config.padding, y_pos), title_text, font=self.font_bold, fill=(0, 0, 0))

        category_text = ticket_data.event.category
        category_width, category_height = self.get_text_dimensions(draw, category_text, self.font_small)
        category_x = self.config.padding + title_width + 10
        category_y = y_pos + 5

        self.create_rounded_rectangle(draw, 
                                    (category_x, category_y,
                                     category_x + category_width + 20,
                                     category_y + category_height + 10),
                                    10, (255, 215, 0))
        draw.text((category_x + 10, category_y + 2), category_text, font=self.font_small, fill=(0, 0, 0))

        y_pos = 260
        details = [
            ('calendar', ticket_data.event.date, 0),
            ('clock', ticket_data.event.time, None),
            ('map', ticket_data.event.location, None),
            ('ticket', ticket_data.event.ticket_type, None)
        ]

        for icon_type, text, x_offset in details:
            if x_offset is None:
                y_pos += 40
                x_pos = self.config.padding
            else:
                x_pos = self.config.padding + x_offset
                
            self.draw_icon_with_text(ticket, x_pos, y_pos, icon_type, text)

        self.add_qr_code(ticket, ticket_data.qr_data)
        return ticket

    def process_background(self, background_path: str, ticket) -> Image.Image:
        background = Image.open(background_path)
        bg_aspect = background.width / background.height
        ticket_aspect = self.config.width / self.config.height

        if bg_aspect > ticket_aspect:
            new_height = self.config.height
            new_width = int(new_height * bg_aspect)
        else:
            new_width = self.config.width
            new_height = int(new_width / bg_aspect)

        background = background.resize((new_width, new_height), Image.LANCZOS)
        
        left = (new_width - self.config.width) / 2
        top = (new_height - self.config.height) / 2
        right = left + self.config.width
        bottom = top + self.config.height
        
        return background.crop((left, top, right, bottom))

    def add_gradient(self, ticket: Image.Image) -> Image.Image:
        gradient = Image.new("RGBA", (self.config.width, self.config.height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(gradient)

        for i in range(self.config.width):
            alpha = int(255 * (1 - i / self.config.width))
            draw.line((i, 0, i, self.config.height), fill=(255, 255, 255, alpha))

        return Image.alpha_composite(ticket.convert("RGBA"), gradient)

    def add_qr_code(self, ticket: Image.Image, qr_data: str):
        qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  
        box_size=8,
        border=2,
    )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_code = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        qr_code = qr_code.resize((320, 320))
        logo = Image.open('./EVNTia.png')
        logo_size = (80, 40)  
        logo = logo.resize(logo_size)
        logo_position = (
            (qr_code.size[0] - logo_size[0]) // 2,  
            (qr_code.size[1] - logo_size[1]) // 2   
        )
        qr_code.paste(logo, logo_position, mask=logo)  
        ticket.paste(qr_code, (830, 50))


if __name__ == "__main__":
    event = EventDetails(
        title="MAGE4",
        category="Concert",
        date="19 Septembre 2024",
        time="14 H",
        location="Antsahamanitra, Antananarivo",
        ticket_type="Bronze",
        url="https://evntia.tech/event/12"
    )

    ticket_data = TicketData(
        ticket_number=12,
        owner="RANDRIAMANANTENA LUCA ZO HAINGO",
        qr_data=event.url,
        event=event
    )
    
    generator = TicketGenerator(icons_folder="icons")
    ticket = generator.generate_ticket("./Mage4.jpg", ticket_data)
    ticket = ticket.convert('RGB')
    ticket.show()