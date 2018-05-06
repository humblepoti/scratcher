import requests
import argparse
import os
import sys
import warnings
import time
import click
import logging


from io import BytesIO
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader
from collections import namedtuple


class Scratcher(object):

    def __init__(self, arg):
        self.url = 'https://www.google.com'
        self.par = '/search?q='
        self.arguments = arg
        self.headers= {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3","Accept-Encoding": "none","Accept-Language": "en-US,en;q=0.8","Connection": "keep-alive"}
        self.domain = self.arguments.domain
        if not self.arguments.extension:
            self.arguments.extension = 'pdf'
        if not self.arguments.output:
            self.arguments.output = ''
        self.author = '/Author'
        self.creation = '/CreationDate'
        self.https = 'https://'
        self.pdf = namedtuple('PDF', 'name author creation')
        self.doc = []
        self.success = 0
        self.failure = 0


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
                Scratcher.log(url,"Unknown error")
                self.failure += 1
            elif pdf is not None:
                self.parsepdf(pdf, url.rsplit('/')[-1])
                self.success += 1
            else:
                Scratcher.log(url,"Content-type of the response is: html")
                self.failure += 1
        else:
            with click.progressbar(url, label='Parsing Files. It might take some while, perhaps you should take a cup of coffee...') as barl:
                for item in barl:
                    pdf = Scratcher.downloadpdf(item)
                    if pdf is 1:
                        Scratcher.log(item,"Unknown error")
                        self.failure += 1
                    elif pdf is not None:
                        self.parsepdf(pdf, item.rsplit('/')[-1])
                        self.success += 1
                    else:
                        Scratcher.log(item, "Content-type of the response is: html")
                        self.failure += 1

        global success
        global failure
        success = self.success
        failure = self.failure

    def downloadpdf(url):
        try:
            request = requests.get(url, verify=False)
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
            s_stdout = sys.stdout
            sys.stdout = BytesIO()
            pdf = PdfFileReader(objbyte)
            sys.stdout = s_stdout
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

    def parsepdf(self, doc, name):
        if doc.getDocumentInfo() is not None:
            if self.author in doc.getDocumentInfo().keys():
                if doc.getDocumentInfo()[self.author]:
                    try:
                        self.doc.append(self.pdf(name, doc.getDocumentInfo()[self.author], doc.getDocumentInfo()[self.creation][2:6]))
                    except KeyError:
                        self.doc.append(
                            self.pdf(name, doc.getDocumentInfo()[self.author], 'Unknown'))

                    global listdocs
                    listdocs = self.doc

    def printer(self, docs):
        print(end='')
        sys.stdout.write('Total Files found:\r')
        sys.stdout.write('\t\t\t\t %d  \r' % len(docs))
        time.sleep(.100)

    def log(item, message):
        logging.basicConfig(filename='example.log', filemode='w', level=logging.DEBUG)
        logging.debug('Error Reason: \t\t'+message+'\t\t caused by: \t'+item)

    def main(argus):
        sys.stdout.write('\n')
        sct = Scratcher(argus)
        obj = sct.returnpage()
        docs = sct.returldocs(obj)
        if docs:
            npages = sct.returlnextp(obj)
            for page in npages:
                obj = sct.returnpage(page)
                docs += sct.returldocs(obj)
                sct.printer(docs)
            warnings.filterwarnings("ignore")
            print('\n')
            sct.verifypdf(docs)
            print('\nTotal Files Successfully Parsed:\t\t\t\t %d  \n' % success)
            print('\nTotal Files Failed in Parsing:  \t\t\t\t %d  \n' % failure)
            print('\nTotal Files With Relevant Metadata:  \t\t\t\t %d  \n' % len(listdocs))
            print('\nDate \t |\t Username\n')
            print('--------------------------------\n')
            for item in sorted(listdocs, key=lambda x: x.creation, reverse=True):
                if item.creation is "Unknown":
                    print(item.creation+'  |\t '+item.author )
                else:
                    print(item.creation+'\t |\t '+item.author)
            print('\n\n++++++++ Finished ++++++++\n')
        else:
            print("\nIt seems you are unlucky!!\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="scratcher.py")
    parser.add_argument('-d', '--domain',  help='a domain to be searched',required=True)
    parser.add_argument('-e', '--extension', help='an extension to be downloaded (default: pdf)',default='pdf')
    parser.add_argument('-o', '--output', help='')
    arguments = parser.parse_args()
    Scratcher.main(arguments)
