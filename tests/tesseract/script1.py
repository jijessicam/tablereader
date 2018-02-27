import pytesseract
from PIL import Image 
import argparse # argparse.ArgumentParser(): for command-line args
import cv2
import os
from wand.image import Image as WandImg 
from pdf2image import convert_from_path, convert_from_bytes 
import tempfile 

#---------------------------------------------------#

filename = "data_1.pdf"

# # Convert filename to image 
# with WandImg(filename=filename, resolution=300) as img:
# 	img.compression_quality = 99
# 	img.save(filename='data_1.png')

# image = cv2.imread('data_1.png')
# gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# # Write grayscale image to disk as temporary file 
# temp = "{}.png".format(os.getpid())
# cv2.imwrite(temp, gray)

# load image as PIL/Pillow image, apply OCR, delete temp file
image = convert_from_path(filename)
text = pytesseract.image_to_string(image)
# text = pytesseract.image_to_string(Image.open(temp))
# os.remove(tempfile)
print(text)

# show output images
cv2.imshow("Image", image)
# cv2.imshow("Output", gray)
cv2.waitkey(0)