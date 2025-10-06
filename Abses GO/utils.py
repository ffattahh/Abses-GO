import openpyxl
from PIL import Image
import io

def extract_qr_from_excel(filename, save_dir="qrs"):
    wb = openpyxl.load_workbook(filename)
    ws = wb.active

    qr_list = []
    for i, image in enumerate(ws._images, start=1):
        img_bytes = image._data()
        img = Image.open(io.BytesIO(img_bytes))
        
        path = f"{save_dir}/qr_{i}.png"
        img.save(path)
        qr_list.append(path)

    print(extract_qr_from_excel("qrsiswa.xlsm"))
    return qr_list