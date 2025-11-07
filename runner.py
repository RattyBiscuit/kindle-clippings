from noter.kindle import ClippingsReader

# from noter.logos import

clipping_reader = ClippingsReader()
clipping_reader.parse()
clipping_reader.make_markdown()
