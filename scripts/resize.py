from PIL import Image
import os

PATH = os.path.abspath(os.path.dirname(__file__))
HEIGHT = 600

def main():
	for filename in os.listdir(PATH):
		if filename.endswith('.png'):
			print(filename)
			filepath = f'{PATH}/{filename}'

			img = Image.open(filepath)

			aspect_ratio = float(img.size[1]) / float(img.size[0])
			height = int(HEIGHT * aspect_ratio)
			resized_img = img.resize((HEIGHT, height))

			resized_img.save(filepath)

if __name__ == '__main__':
	main()
