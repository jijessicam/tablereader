import pytesseract
from PIL import Image 
import argparse # argparse.ArgumentParser(): for command-line args
import cv2
import os
from wand.image import Image as WandImg 

#---------------------------------------------------#

filename = "data_1.pdf"

# Convert filename to image 
with WandImg(filename=filename, resolution=300) as img:
	img.compression_quality = 99
	img.save(filename='data_1.png')

image = cv2.imread('data_1.png')
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Write grayscale image to disk as temporary file 
tempfile = "{}.png".format(os.getpid())
cv2.imwrite(tempfile, gray)

# load image as PIL/Pillow image, apply OCR, delete temp file
text = pytesseract.image_to_string(Image.open(tempfile))
os.remove(tempfile)
print(text)

# show output images
cv2.imshow("Image", image)
cv2.imshow("Output", gray)
cv2.waitkey(0)