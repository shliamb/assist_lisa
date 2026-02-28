from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306

serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)


def image(text, x, y):
    image = Image.new('1', (device.width, device.height))
    draw = ImageDraw.Draw(image)
    # font = ImageFont.load_default() только англ
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    draw.text((x, y), text, font=font, fill=255)
    device.display(image)