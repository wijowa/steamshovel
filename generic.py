'''
Created on Jun 7, 2012

Library for data mining and piling

@author: Williqm
'''
import sqlite3
import math
import urllib
import xlrd
import datetime
import json
import re
from xml.dom import minidom
#import simplejson as json

db = sqlite3.connect('tables.db')


def get_lat_long(location):
    key = ""
    output = "csv"
    location = urllib.quote_plus(location)
    request = "http://maps.google.com/maps/geo?q=%s&output=%s&key=%s" % (location, output, key)
    data = urllib.urlopen(request).read()
    dlist = data.split(',')
    if dlist[0] == '200':
        return dlist[2], dlist[3]
    else:
        return None, None
    
def calculate_distance(LL1, LL2):
    '''
        returns distance in mi
        accepts two tuples: (Lat1, Lon1)=LL1, (Lat2, Lon2)=LL2
    '''
    lat1, lon1 = LL1
    lat2, lon2 = LL2
    
    lat1 = float(lat1) * math.pi/180
    lon1 = float(lon1) * math.pi/180
    lat2 = float(lat2) * math.pi/180
    lon2 = float(lon2) * math.pi/180
    
    return 3959.0 * math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon2-lon1))



            
       
''' Intermediate Data Types Below '''

class Document:
    ''' Basic document type.  Defaults to a filename which is read into the file attribute
    '''
    filename=''
    
    file=None
    #value = {}
    #def __getattr__(self, key):
    #    return self.value[key]
    def __init__(self, filename):
        self.filename=filename
        self.file=open(filename, 'r')
        
    @property
    def value(self):
        return self.file.read()

class Url(Document):
    url=''
    file=None
    def __init__(self,url):
        self.url=url
        self.file = urllib.urlopen(url)  
        
    def __repr__(self):
        return self.value
        
class XlsTable(Document):
    '''
        XlsTable is an iterable that returns a dict for each row in the xls spreadsheet,
        with keys generated from the header of each column in the spreadsheet,
        basically treats a spreadsheet generically of the format:
        Col1 Title    Col2 Title      Col3 Title    ...  (name_row)
        R1C1          R1C2            R1C3          ...  (start_row)
        R2C1          R2C2            R2C3          ...
        ...           ...             ...
        Types are automatically inferred from the type described by the Excel format.
        @usage:        
    '''
    colnames=[]
    _coltypes=[]
    name_row=0
    start_row=1
    row=start_row
    _sheet=0
    def __len__(self):
        return self.sheet.nrows-self.start_row
    
    def next(self):
        if(self.row<len(self)):
            self.row+=1
            return self[self.row]
        else:
            raise StopIteration
    
    def __getitem__(self, n):
        return [c(f) for c,f in zip(self._coltypes,self.sheet.row_values(n))]
    def __iter__(self):
        return self
    def __repr__(self):
        return '%s Table' % self.filename
    def xlsfloat(self, value):
        try:
            i=int(value)
        except ValueError:
            return None
        if(i==value):
            return i
        else:
            return float(value)
    def xlsdate(self, value):
        return datetime.datetime(*xlrd.xldate_as_tuple(value, self.book.datemode))
    @property
    def sheet(self):
        return self.book.sheets()[self._sheet]
    def __init__(self, file, name_row=0, start_row=1, sheet=0):
        self.name_row = name_row
        self.start_row = start_row
        self._sheet=sheet
        self.book = xlrd.open_workbook(file)
        self.colnames = [re.sub('[\W]', '', name) for name in self.sheet.row_values(self.name_row)]
        self._coltypes = [[str,str,self.xlsfloat,self.xlsdate][v] for v in self.sheet.row_types(self.start_row)]
        
class JsonDocument(Document):    
    @property
    def value(self):
        return json.loads(self.file.read())
    def __dict__(self):
        return self.value        
    def __getattr__(self, k):
        return self.value[k]
    
class XmlElement():
    ''' XmlElement is a simple auto nesting data mask for XML data.  
        Well adapted to list formatted arbitrary data - i.e. multiple successive elements with the same name, 
        that become lists inside the XmlElement object.  Not particularly well suited to text markup.
        Element Attributes are stored in the "attributes" attribute
        of the XmlElement object.
        Element Content is stored in the "value" attribute of the XmlElement object.     
        @usage:
        document = """\
        <tag1>
            <listtag attribute="true">
                Value
            </listtag>
            <listtag>
                Value2
            </listtag>
            <listtag>
                Value3
            </listtag>
            <tag2>
                Value4
            </tag2>
        </tag1>
        """
        >>> element =  xml.dom.minidom.parseString(document)
        >>> v = XmlElement(element)
        >>> v.tag1.listtag[0].value
        Value
        >>> v.tag1.tag2.value
        Value4
        >>> v.tag1.listtag[0].attributes
        {u'attribute': u'true'}
    '''
    value=''
    attributes={}
    def __init__(self,element):
        '''  Node type reference: 
        ELEMENT_NODE                = 1
        ATTRIBUTE_NODE              = 2
        TEXT_NODE                   = 3
        CDATA_SECTION_NODE          = 4
        ENTITY_REFERENCE_NODE       = 5
        ENTITY_NODE                 = 6
        PROCESSING_INSTRUCTION_NODE = 7
        COMMENT_NODE                = 8
        DOCUMENT_NODE               = 9
        DOCUMENT_TYPE_NODE          = 10
        DOCUMENT_FRAGMENT_NODE      = 11
        NOTATION_NODE               = 12
        '''
        self.dom=element
        for child in element.childNodes:
            if child.nodeType==element.ELEMENT_NODE:
                try:
                    a=getattr(self, child.nodeName)
                    if(type(a) not in [type([])]):
                        a=[a]
                    a.append(XmlElement(child))         
                    setattr(self,child.nodeName, a)          
                except AttributeError:
                    setattr(self, child.nodeName, XmlElement(child))             
            elif child.nodeType==element.ATTRIBUTE_NODE:
                 self.attributes[child.nodeName]=child.data
            elif child.nodeType==element.TEXT_NODE:
                self.value+=(child.data.strip())
        try:
            for k,v in element.attributes.items():
                self.attributes[k]=v
        except AttributeError:
            pass  
    def __repr__(self):
        return self.value    
    
class XmlDocument(Document):
    dom=None
    @property
    def value(self):
        if(self.dom==None):
            self.dom = minidom.parse(self.file)
        return XmlElement(self.dom) 
    def __repr__(self):
        return self.value
        
class XmlUrl(Url, XmlDocument):
    ''' The Python value output of a XML encoded URL
        @usage
            >>> v = XmlUrl(url)
            >>> v.value
            {}
            
            GetAttr can be used to access values using [] notation directly
            XmlUrl demonstrates nesting functionality of this toolbox.
            Since it subclasses Url and XmlDocument, those classes provide
            all the methods needed to access a Url as a Xml document.
    '''
    pass
        
class JsonUrl(Url, JsonDocument):
    ''' The Python value output of a JSON encoded URL
        @usage
            >>> v = JsonUrl(url)
            >>> v.value
            {}
            
            GetAttr can be used to access values using [] notation directly
        @note:
            JsonUrl demonstrates nesting functionality of this toolbox.
            Since it subclasses Url and JsonDocument, those classes provide
            all the methods needed to access a Url as a Json document.
    '''
    pass

        
class EnergyPrice(JsonUrl):
    ''' Returns a dict of the output of the NREL utility price app
        @usage 
            >>> EnergyPrice('11206').residential
            0.209999999999            
        @note
            typical url: http://developer.nrel.gov/api/georeserv/service/utility_rates.json?address=11206&api_key=xxxx
            typical response: {"errors": [{}], "infos": [], "inputs": {"address": "11206"}, 
                                "outputs": {"commercial": 0.17999999999999999, "company_id": "04226", 
                                            "industrial": 0.17000000000000001, "name": "Consolidated Edison Co. Of New York Inc.", 
                                            "residential": 0.20999999999999999}, 
                                "version": "2.1.7", "warnings": []}
                   
            
    '''
    _api_key='42d719e7c42834f7a7f6ca07e8642368d2185e15'
    _url='http://developer.nrel.gov/api/georeserv/service/utility_rates.json'
    address = None
    def __init__(self, address):
        self.address = address
        self.url = '%s?address=%s&api_key=%s'%(self._url, self.address, self._api_key)
        self.file=JsonUrl(self.url).file
        #self.value =  json.loads(.read())['outputs']
        
class Location(XmlUrl):
    ''' Generates a dict of the xml result of the Yahoo placefinder API
        @usage:
            >>> l = Location('11206')
            >>> l.latitude
            40.702690
            >>> l.longitude
            -73.942430
            
    '''
    _url='http://where.yahooapis.com/geocode'
    _appid='WZzPGD5i'
    location = ''
    def __init__(self, location):
        self.location=location
        self.url = '%s?q=%s&appid=%s' % (self._url, self.location, self._appid)
        self.file = XmlUrl(self.url).file
    def __getattr__(self,k):
        try:
            return getattr(self.value.ResultSet.Result,k)
        except AttributeError:
            try:
                return getattr(self.value.ResultSet,k)
            except AttributeError:
                return getattr(self.value,k)

class CensusTable(XlsTable):
    ''' Contains tables from Census 
        (nothing here yet)
    '''
    def __init__(self):
        pass

     
class SQLiteTable(object):
    name=None
    python_to_sql = {'str':'VARCHAR(255)',
             'text':'TEXT',
             'int':'INT',
             'float':'DOUBLE',
             'datetime':'DATETIME'
             }
    @classmethod
    def sql_typeof(cls,*args):
        return [cls.python_to_sql[type(v).__name__] for v in args]
    def __init__(self, name, cols, types, db):
        ''' Constructor initializes table or initializes self with existing table '''
        self.name=name
        self.db=db
        self.dbc=db.cursor()
        columns = ','.join(['%s %s'%(n,t) for n,t in zip(cols,types)])
        q = 'CREATE TABLE IF NOT EXISTS %s (%s);' % (name, columns)
        print q
        self.dbc.execute(q) 
        self.db.commit()
    def addcolumn(self, name, type):
        self.dbc.execute('ALTER TABLE %s ADD COLUMN %s %s' % (self.name, name, type))
    def addrow(self, *args):
        args2=[]
        for arg in args:
            if(type(arg).__name__=='str'):                
                args2.append("'%s'"%arg)
            elif(type(arg).__name__=='datetime'):
                args2.append("'%s'"%arg.strftime('%Y-%m-%d'))
            else:    
                args2.append(str(arg))
        q = 'INSERT INTO %s VALUES (%s)' %(self.name, ', '.join(args2))
        print q
        self.dbc.execute(q)
        self.db.commit()
    def update(self, **kwargs):
        pass
    def get(self, cols=['*'], n=None):
        columns = ', '.join(cols)
        limit = ''
        if n!=None:
            limit = 'LIMIT %d'%n
        where = ''
        query = 'SELECT %s FROM %s %s %s'%(columns, self.name, where, limit)
        