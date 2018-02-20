import PyPDF2
import pdftables_api 

# --------------------------------------------------------

filename = "data_1.pdf"
api_key = "k1obraaerb7y"

# pfr = PyPDF2.PdfFileReader(open(filename, "rb")) #filereader object


pdftables = pdftables_api.Client(api_key)
pdftables.csv(filename, 'data_1_result.csv')
