"""用捆绑 Python（含 reportlab）创建 Day16 教学样例，不需要 OCR。"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
output_path = ROOT / "output" / "pdf" / "day16_mixed_sample.pdf"
if output_path.exists():
    raise FileExistsError(output_path)
output_path.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 38)


def raster(text: str) -> ImageReader:
    image = Image.new("RGB", (1400, 180), "white")
    ImageDraw.Draw(image).text((45, 65), text, font=font, fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


application = "用户可在购买后7天内申请退款。"
usage = "累计使用时长超过2小时的订单不支持退款。"
arrival = "审核通过后，退款将在3个工作日内原路退回。"
pdf = canvas.Canvas(str(output_path), pagesize=A4)


def heading(text: str) -> None:
    pdf.setFont("STSong-Light", 19)
    pdf.drawString(50, 775, text)
    pdf.setFont("STSong-Light", 13)
    pdf.drawString(50, 745, "虚构教学语料，仅用于验证文字层与图片混合解析。")


heading("第1页：普通文字页")
pdf.drawString(50, 660, application)
pdf.showPage()

# 真正无文字层的一页，标题也包含在图片内。
pdf.drawImage(raster(usage), 50, 530, width=495, height=64)
pdf.showPage()

heading("第3页：文字与两张图片混合")
pdf.drawString(50, 690, "退款说明：关键规则位于下面两张图片中。")
pdf.drawImage(raster(application), 50, 540, width=495, height=64)
pdf.drawImage(raster(arrival), 50, 410, width=495, height=64)
pdf.showPage()

heading("第4页：图片与隐藏文字层重复")
pdf.drawImage(raster(arrival), 50, 480, width=495, height=64)
hidden = pdf.beginText(65, 500)
hidden.setFont("STSong-Light", 13)
hidden.setTextRenderMode(3)
hidden.textLine(arrival)
pdf.drawText(hidden)
pdf.showPage()

# 最后一页故意留空，验证不会丢失后续诊断或误判识别成功。
pdf.showPage()
pdf.save()
print(output_path)
