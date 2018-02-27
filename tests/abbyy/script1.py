from ABBYY import CloudOCR 
import xml.etree.ElementTree as ET 
import pandas as pd 

# --------------------------------------------------------#

class XMLConverter:

    def __init__(self, input_data):
        self.root = ET.XML(input_data)

    # return list of dictionaries from text and attributes of children
    # under XML root 
    def parse_root(self, root):
        return [self.parse_element(child) for child in iter(root)]

    # collect {key:attribute} and {tag:text} from the XML element
    # and all of its children into a single dict of strings
    def parse_element(self, element, parsed=None):
        if parsed is None:
            parsed = dict()
        for key in element.keys():
            parsed[key] = element.attrib.get(key)
        if element.text:
            parsed[element.tag] = element.text
        for child in list(element): # Recurse 
            self.parse_element(child, parsed)
        return parsed

        # Inititate root XML, parse it, return pandas DataFrame 
    def process_data(self):
        structure_data = self.parse_root(self.root)
        return pd.DataFrame(structure_data)


def main():

    ocr_engine = CloudOCR(application_id='tablereader-18', password='AvgAPRIhCnap+G07WX7KhDUV ')

    pdf = open('data_1.pdf', 'rb')
    file = {pdf.name: pdf}

    ocr_output = ocr_engine.process_and_download(file, exportFormat='xml,pdfTextAndImages')
    result = ocr_output.get('xml').getvalue()

    parsexml = XMLConverter(result)
    df_result = parsexml.process_data()
    print df_result 

if __name__ == "__main__":
    main()