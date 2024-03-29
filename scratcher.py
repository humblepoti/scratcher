import requests
import argparse
import os
import sys
import warnings
import time
import click
import logging
import csv

from io import BytesIO
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, utils
from collections import namedtuple


class Scratcher(object):

    def __init__(self, arg):
        self.url = 'https://www.google.com'
        self.par = '/search?num=100&q='
        self.arguments = arg
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Charset":
                        "ISO-8859-1,utf-8;q=0.7,*;q=0.3", "Accept-Encoding": "none", "Accept-Language":
                        "en-US,en;q=0.8", "Connection": "keep-alive"}
        self.domain = self.arguments.domain
        if self.arguments.tor:
            self.proxies = dict(http='socks5://'+self.arguments.tor, https='socks5://'+self.arguments.tor)
        else:
           self.arguments.tor = 'normal'
        if not self.arguments.ext:
            self.arguments.ext = 'pdf'
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
        if self.arguments.tor == 'tor':
            if not url:
                request = requests.get(self.url + self.par + "site:" + self.domain + " ext:" + self.arguments.ext,
                                       headers=self.headers, proxies=self.proxies)
            else:
                request = requests.get(url, headers=self.headers, proxies=self.proxies)
        else:
            if not url:
                request = requests.get(self.url+self.par+"site:"+self.domain+" ext:"+self.arguments.ext,
                                       headers=self.headers)
            else:
                request = requests.get(url, headers=self.headers)
        bsobj = BeautifulSoup(request.text, "html.parser")
        
        if bsobj.findAll('a')[-1]['href'].strip('//') == 'support.google.com/websearch/answer/86640':
            sys.exit(
                "\nGoogle has perceived that your are poking around its search engine and it is blocking you!!! Wait "
                "for some time to try again through this network.\n\n")
        return bsobj

    def returldocs(self, bsobj):
        udocument = bsobj.findAll('div', {'class': 'g'})
        urldlist = [item.a['href'] for item in udocument]
        return urldlist

    def returlnextp(self, bsobj):
        nextpages = bsobj.findAll('a', {'id': 'pnnext'})
        urlnplist = [self.url + item['href'] for item in nextpages if item.span is not None]
        return urlnplist

    def verifypdf(self, url):
        if type(url) is not list:
            pdf = Scratcher.downloadpdf(url)
            if pdf == 1:
                Scratcher.log(url,"Unknown error")
                self.failure += 1
            elif pdf == 2:
                self.failure += 1
            elif pdf is not None:
                self.parsepdf(pdf, url.rsplit('/')[-1])
                self.success += 1
            else:
                Scratcher.log(url,"Content-type of the response is: html")
                self.failure += 1
        else:
            with click.progressbar(url, label='Parsing Files. It might take some while, perhaps you wanna take a '
                                              'cup of coffee...') as barl:
                for item in barl:
                    pdf = Scratcher.downloadpdf(item)
                    if pdf == 1:
                        Scratcher.log(item,"Unknown error")
                        self.failure += 1
                    elif pdf == 2:
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
            if 'Content-Type' in request.headers.keys():
                if request.headers['Content-Type'] == 'text/html':
                    return None
        except requests.exceptions.ConnectionError:
            sys.exit("\nThere was an error when trying to connect to the domain. Please confirm if the domain is "
                     "correctly written.\n")
        try:
            objbyte = BytesIO(request.content)
        except Exception as e:
            Scratcher.log(url, e)
            sys.exit(
                "\nThere was an error when trying to convert the content of the response.Please verify the logs to"
                " see the raised error.\n")
        try:
            pdf = PdfFileReader(objbyte)
        except utils.PdfReadError as e:
            Scratcher.log(url, e)
            obje = BytesIO(request.content.strip(b'\x00'))
            try:
                pdf = PdfFileReader(obje)
            except utils.PdfReadError:
                return 2
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
        if out == 0:
            filename = open(decfile[-1], 'rb')
            try:
                pdf = PdfFileReader(filename)
            except utils.PdfReadError:
                return 2
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
                        self.doc.append(self.pdf(name, doc.getDocumentInfo()[self.author],
                                                 doc.getDocumentInfo()[self.creation][2:6]))
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
        logging.basicConfig(filename='scratcher.log', filemode='w', level=logging.DEBUG)
        logging.debug('Error Reason: \t\t'+str(message)+'\t\t caused by: \t'+item)

    def exec(self):
        obj = self.returnpage()
        docs = self.returldocs(obj)
        if docs:
            npages = self.returlnextp(obj)
            if npages:
                nobj = self.returnpage(npages[-1])
                nextpages = [page for page in self.returlnextp(nobj) if not page in npages]
                if nextpages:
                    npages = npages + nextpages
                for page in npages:
                    obj = self.returnpage(page)
                    docs += self.returldocs(obj)
                    self.printer(docs)
            else:
                self.printer(docs)
            warnings.filterwarnings("ignore")
            print('\n')
            self.verifypdf(docs)
            print('\nTotal Files Successfully Parsed:\t\t\t\t %d  \n' % success)
            print('\nTotal Files Failed in Parsing:  \t\t\t\t %d  \n' % failure)
            try:
                listdocs
                print('\nTotal Files With Relevant Metadata:  \t\t\t\t %d  \n' % len(listdocs))
                print('\nDate \t |\t Username\n')
                print('--------------------------------\n')
                for item in sorted(listdocs, key=lambda x: x.creation, reverse=True):
                    if item.creation == "Unknown":
                        print(item.creation + '  |\t ' + item.author)
                    else:
                        print(item.creation + '\t |\t ' + item.author)
                self.writecsv()
            except NameError:
                    print('\nTotal Files With Relevant Metadata:  \t\t\t\t 0  \n')
            print('\n\n++++++++++++++++ Finished ++++++++++++++++\n')
        else:
            sys.exit("\nIt seems you are unlucky!!\n")

    def writecsv(self):
        listauthor = [item.author for item in sorted(listdocs, key=lambda x: x.creation, reverse=True)]
        listauthor = set(listauthor)
        if self.arguments.output:
            with open(self.arguments.output, 'a') as csvfile:
                csv_w = csv.writer(csvfile)
                csv_w.writerow(listauthor)
        else:
            with open('output.csv', 'a') as csvfile:
                csv_w = csv.writer(csvfile)
                csv_w.writerow(listauthor)


    def main(argus):
        sys.stdout.write('\n')
        sct = Scratcher(argus)
        sct.exec()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="scratcher.py")
    parser.add_argument('-d', '--domain',  help='a domain to be searched', required=True, metavar='www.example.com')
    parser.add_argument('-e', '--ext', help='an extension to be downloaded (default: pdf)', default='pdf', metavar='pdf')
    parser.add_argument('-t', '--tor', help='an option to specify tor usage (default: non-tor usage)', metavar='host:'
                                                                                                               'port')
    parser.add_argument('-o', '--output', help='a name for the output file. Default is output.csv', metavar='file.csv')
    arguments = parser.parse_args()
    Scratcher.main(arguments)
