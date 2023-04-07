from PIL import Image
import os

PATH = os.path.abspath(os.path.dirname(__file__))

def main():
	for filename in os.listdir(PATH):
		if filename.endswith('.png'):
			print(filename)
			filepath = f'{PATH}/{filename}'

			image = Image.open(filepath).convert('RGBA')

			width, height = image.size
			for x in range(width):
				for y in range(height):
					r, g, b, a = image.getpixel((x, y))
					if a != 0:
						image.putpixel((x, y), (0, 0, 0, a))

			image.save(filepath)

if __name__ == '__main__':
	main()
