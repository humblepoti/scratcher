import requests
import argparse
import os
import sys

from io import BytesIO
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader


class Scratcher(object):

    def __init__(self, arg):
        self.url = 'https://www.google.com'
        self.par = '/search?q='
        self.arguments = arg
        self.headers= {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML like Gecko) Chrome/23.0.1271.64 Safari/537.11", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3","Accept-Encoding": "none","Accept-Language": "en-US,en;q=0.8","Connection": "keep-alive"}
        self.domain = self.arguments.domain
        if not self.arguments.extension:
            self.arguments.extension = 'pdf'
        if not self.arguments.output:
            self.arguments.output = ''
        self.author = '/Author'
        self.https = 'https://'

    def returnpage(self, url=None):
        if not url:
            request = requests.get(self.url+self.par+"site:"+self.domain+" ext:"+self.arguments.extension, headers=self.headers)

        else:
            request = requests.get(url, headers=self.headers)


        bsobj = BeautifulSoup(request.text, "html.parser")

        return bsobj

    def returldocs(self, bsobj):
        udocument = bsobj.findAll('h3', {'class': 'r'})
        urldlist = [item.a['href'] for item in udocument]
        return urldlist

    def returlnextp(self, bsobj):
        nextpages = bsobj.findAll('a', {'class': 'fl'})
        urlnplist = [self.url + item['href'] for item in nextpages if item.span is not None]
        return urlnplist

    def verifypdf(self, url):
        if type(url) is not list:
            pdf = Scratcher.downloadpdf(url)
            if pdf is 1:
                print("\n Unknown error")
            elif pdf is not None:
                self.parsepdf(pdf)
            else:
                print("\n Content-type is of the response is: html")
        else:
            for item in url:
                print(item)
                pdf = Scratcher.downloadpdf(item)
                if pdf is 1:
                    print("\n Unknown error")
                elif pdf is not None:
                    self.parsepdf(pdf)
                else:
                    print("\n Content-type is of the response is: html")

    def downloadpdf(url):
        try:
            request = requests.get(url)
            if request.headers['Content-Type'] == 'text/html':
                return None
        except requests.exceptions.ConnectionError:
            sys.exit("\nThere was an error when trying to connect to the domain. Please confirm if the domain is correctly written.\n")
        try:
            objbyte = BytesIO(request.content)
        except Exception as e:
            print(e)
            return None
        try:
            pdf = PdfFileReader(objbyte)
        except Exception as e:
            print(e)
            return None
        if pdf.getIsEncrypted() is True:
            try:
                pdf.decrypt('')

            except:
                pdf = Scratcher.handlepdf(request.content)

        return pdf

    def handlepdf(response):
        decfile = ['meta.pdf', 'out.pdf']
        with open(decfile[0], 'wb') as file:
            file.write(response)
        command = "qpdf --password='' --decrypt "+decfile[0]+" "+decfile[-1]
        out = os.system(command)
        if out is 0:
            filename = open(decfile[-1], 'rb')
            pdf = PdfFileReader(filename)
            for item in decfile:
                os.system("rm "+item)
        else:
            return 1

        return pdf

    def parsepdf(self, doc):
        if doc.isEncrypted is True:
          doc.decrypt('')
        if doc.getDocumentInfo() is not None:
            if self.author in doc.getDocumentInfo().keys():
                print(doc.getDocumentInfo()[self.author])
                print(doc.getDocumentInfo()['/CreationDate'])

    def main(argus):
        sct = Scratcher(argus)
        obj = sct.returnpage()
        docs = sct.returldocs(obj)
        if docs:
            npages = sct.returlnextp(obj)
            for page in npages:
                print(page)
                obj = sct.returnpage(page)
                docs += sct.returldocs(obj)
            print(len(docs))
            sct.verifypdf(docs)
        else:
            print("\nIt seems you are unlucky!!\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="scratcher.py")
    parser.add_argument('-d', '--domain',  help='a domain to be searched',required=True)
    parser.add_argument('-e', '--extension', help='an extension to be downloaded (default: pdf)',default='pdf')
    parser.add_argument('-o', '--output', help='')
    arguments = parser.parse_args()
    Scratcher.main(arguments)
