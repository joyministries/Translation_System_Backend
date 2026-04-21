import fitz
import pytesseract
import cv2
import numpy as np
from PIL import Image
from deep_translator import GoogleTranslator


def translate_pdf(input_path, output_path, target_lang="sw"):
    translator = GoogleTranslator(source="auto", target=target_lang)

    doc = fitz.open(input_path)
    new_doc = fitz.open()

    for page_num in range(len(doc)):
        page = doc[page_num]

        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)

        data = pytesseract.image_to_data(img_np, output_type=pytesseract.Output.DICT)

        page_height = page.rect.height
        footer_threshold = page_height * 0.90

        for i in range(len(data["text"])):
            text = data["text"][i]

            if not text.strip():
                continue

            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            font_size = data["height"][i]
            text_color = data["color"][i] if data["color"][i] != 0 else 0

            if page_num == 0:
                if y >= footer_threshold:
                    translated = translator.translate(text)

                    cv2.rectangle(img_np, (x, y), (x + w, y + h), (255, 255, 255), -1)

                    color_bgr = (
                        (0, 0, 0)
                        if text_color == 0
                        else (text_color, text_color, text_color)
                    )
                    cv2.putText(
                        img_np,
                        translated,
                        (x, y + h),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_size / 30,
                        color_bgr,
                        2,
                    )
            else:
                translated = translator.translate(text)

                cv2.rectangle(img_np, (x, y), (x + w, y + h), (255, 255, 255), -1)

                color_bgr = (
                    (0, 0, 0)
                    if text_color == 0
                    else (text_color, text_color, text_color)
                )
                cv2.putText(
                    img_np,
                    translated,
                    (x, y + h),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_size / 30,
                    color_bgr,
                    1,
                )

        new_img = Image.fromarray(img_np)
        new_pdf = fitz.open()
        new_pdf.insert_page(0, width=new_img.width, height=new_img.height)

        pix = fitz.Pixmap(fitz.csRGB, fitz.Pixmap(new_img.tobytes(), new_img.size))
        new_pdf[0].insert_image(new_pdf[0].rect, pixmap=pix)

        new_doc.insert_pdf(new_pdf)

    new_doc.save(output_path)
    print(f"Translation complete: {output_path}")


if __name__ == "__main__":
    input_file = "storage/input.pdf"
    output_file = "storage/translated_output.pdf"

    translate_pdf(input_file, output_file, target_lang="sw")
