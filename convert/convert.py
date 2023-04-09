from PIL import Image
import os

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STAGE_PATH = os.path.join(ROOT_PATH, 'scripts')
HEIGHT = 600

def main():
	for filename in os.listdir(STAGE_PATH):
		if filename.endswith('.png'):
			print(f"Processing: {filename.replace('.png', '')}")

			# resize
			filepath = os.path.join(STAGE_PATH, filename)
			image = Image.open(filepath)

			aspect_ratio = float(image.size[1]) / float(image.size[0])
			height = int(HEIGHT * aspect_ratio)
			image = image.resize((HEIGHT, height))

			out_path = os.path.join(ROOT_PATH, 'img', 'unhidden', filename)
			image.save(out_path)

			# hide
			filepath = os.path.join(ROOT_PATH, 'img', 'unhidden', filename)
			image = Image.open(filepath).convert('RGBA')

			width, height = image.size
			for x in range(width):
				for y in range(height):
					r, g, b, a = image.getpixel((x, y))
					if a != 0:
						image.putpixel((x, y), (0, 0, 0, a))

			out_path = os.path.join(ROOT_PATH, 'img', 'hidden', filename)
			image.save(out_path)

			# delete staging file
			os.remove(os.path.join(STAGE_PATH, filename))

if __name__ == '__main__':
	main()
