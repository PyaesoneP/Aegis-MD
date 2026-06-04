import pymupdf

doc = pymupdf.open("data/guidelines/5506cpg1.pdf")
out = open("output.txt", "wb")

for page in doc:
    text = page.get_text().encode("utf-8")
    out.write(text)
    out.write(bytes((12,)))
out.close()