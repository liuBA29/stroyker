from PIL import Image


def create_watermark(img_input, watermark_img, **kwargs):
    output_name = kwargs.get('output_name')

    main = Image.open(img_input)
    mark = Image.open(watermark_img)
    main.has_watermarked = 1

    tmp_img = Image.new('L', main.size)
    for i in range(0, tmp_img.size[0], mark.size[0]):
        for j in range(0, tmp_img.size[1], mark.size[1]):
            main.paste(mark, (i, j), mark)

    img_output = main.filename

    if output_name:
        img_output = img_output.replace(
            main.filename.split('/')[-1], output_name)

    main.save(img_output)
    return img_output
