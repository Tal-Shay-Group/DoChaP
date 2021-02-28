import re
from sqlite3 import connect
from Director import Director
from InterproCollector import InterProBuilder
from conf import external
from recordTypes import *
import pandas as pd


class DomainOrganizer:

    def __init__(self, download=False):
        self.allDomains = dict()  # keys are id, vals are tuple combined from Domain object info
        self.internalID = 0
        self.allExt = dict()
        self.allNames = dict()
        self.allCDD = dict()
        self.ignored_domains = {"nonInterpro": [], "onlyInterpro": [], "family": []}
        director = Director()
        self.Interpro = InterProBuilder()
        director.setBuilder(self.Interpro)
        director.collectFromSource(download=download)

    def collectDatafromDB(self, dbname='DB_merged.sqlite'):
        """collect domains data from existing SQLite database to keep the same TypeID for the same domains"""
        con = connect(dbname)
        cur = con.cursor()
        self.internalID = list(cur.execute("SELECT COUNT(*) FROM DomainType"))[0][0]
        cur.execute('SELECT * FROM DomainType')
        for ud in cur.fetchall():
            c_ud = tuple(ud)
            self.allDomains[c_ud[0]] = c_ud[1:]
            self.allNames[c_ud[1]] = c_ud[0]
            for u_ext in c_ud[5:]:
                if u_ext is not None:
                    self.allExt[u_ext] = c_ud[0]
            self.allCDD[c_ud[4]] = c_ud[0]

    def addDomain(self, domain):
        """ Takes a domain object and add it to the allDomains attribute,
        by merging it to an existing domain ID or assigning a new domain ID, domains must:
            1 - have a valid external id ('cdd', 'pfam', 'smart', 'tigrfams', 'interpro'
            2 - have at least one of the external IDs: 'cdd', 'pfam', 'smart', 'tigrfams'
            ** Interpro alone is not enough!!
        Domains records are merged into the same domain ID if:
            1 - Interpro has connected the external ID
            2 - The domains has the same CDD
        New DomainID will be given otherwise
        @return: domain ID of the domain in the allDomain attr. None if the domain was not added into the allDomain attr
        """
        currReg = None
        existExt = [None] * 5  # stand for ['cdd', 'pfam', 'smart', 'tigrfams', 'interpro']
        repeat = False
        if domain.extID is None:
            return None
        elif domain.extType not in external:
            return None
        identify = self.Interpro.AllDomains.loc[
            self.Interpro.AllDomains[domain.extType].str.contains(domain.extID, na=False)]
        ind = identify.index.values[0] if len(identify) != 0 else None
        if ind is not None:
            # self.ignored_domains["nonInterpro"].append(domain.extID)
            # return None  # only using domains that are recorded in Interpro
            if domain.extType == "interpro" and \
                    [identify["cdd"][0], identify["pfam"][0], identify["smart"][0], identify['tigrfams'][0]] == [None] * 4:
                self.ignored_domains["onlyInterpro"].append(domain.extID)
                return None  # interpro domains are only used when connected with other external source
            elif self.Interpro.AllDomains.loc[ind, "Type"] not in ("domain", "repeat"):
                self.ignored_domains["family"].append(domain.extID)
                return None  # only using "domain" and not "family"

        if self.Interpro.AllDomains.loc[ind, "Type"] == "repeat":
            repeat = True

        if domain.extID in self.allExt:
            currReg = self.allExt[domain.extID]
            ncdd = self.cddAdd(domain, currReg)
            ndesc = self.noteAdd(domain, currReg)
            existExt = self.allDomains[currReg][4:]
            cdname, oname = self.mainNameOtherName(domain, currReg)
        elif ind in self.allExt:
            currReg = self.allExt[ind]
            ncdd = self.cddAdd(domain, currReg)
            ndesc = self.noteAdd(domain, currReg)
            existExt = self.allDomains[currReg][4:]
            cdname, oname = self.mainNameOtherName(domain, currReg)
        else:
            if domain.cdd is not None and domain.cdd in self.allCDD:
                existExt = list(self.allDomains[self.allCDD[domain.cdd]][4:])
                currReg = self.allCDD[domain.cdd]
                ndesc = self.noteAdd(domain, currReg)
                cdname, oname = self.mainNameOtherName(domain, currReg)
                ncdd = str(self.allDomains[currReg][3])
            else:
                self.internalID += 1
                cdname = domain.name
                oname = domain.name
                currReg = self.internalID
                ndesc = domain.note
                ncdd = domain.cdd
        if ind is not None and ind not in self.allExt:
            indExt = [identify["cdd"][0], identify["pfam"][0], identify["smart"][0], identify['tigrfams'][0], ind]
            existExt = tuple(map(self.addToExtID, list(existExt), indExt))
            self.allExt[ind] = currReg
        pos = external.index(domain.extType)
        tempexist = list(existExt).copy()
        tempexist[pos] = self.addToExtID(domain.extID, tempexist[pos])
        existExt = tuple(tempexist)
        if not (existExt[pos].startswith(re.sub(r'\d+$', '', domain.extID)) or
                (domain.extID[0:2] == "cl" and pos == 0)):
            raise ValueError('External id type not in correct location!')
        if repeat:
            if ndesc is None or len(ndesc) == 0:
                ndesc = "Repeat_domain"
            else:
                ndesc = ndesc + "; Repeat_domain" if "; Repeat_domain" not in ndesc else ndesc
        ndesc = "; ".join(list(set(ndesc.split("; ")))) if ndesc is not None else ndesc
        # insert into dict
        self.allDomains[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
        self.allExt[domain.extID] = currReg
        self.allNames[domain.name] = currReg
        self.allCDD[domain.cdd] = currReg
        if domain.extType == "interpro":
            return None  # Domains of source "interpro" holds usful data - short name etc. but might be predicted by unsupported DB, therefore - ignored
        return currReg

    def mainNameOtherName(self, domain, currReg):
        """Choose the shortest name among similar records."""
        cdname = self.allDomains[currReg][0]
        oname = self.allDomains[currReg][1]
        if domain.name is not None:
            if cdname is None:
                cdname = domain.name
            elif len(domain.name) < len(cdname):
                if oname is None:
                    oname = cdname
                elif cdname.lower() not in oname.lower():
                    oname = self.allDomains[currReg][1] + '; ' + cdname
                cdname = domain.name
            else:
                if oname is None:
                    oname = domain.name
                elif domain.name.lower() not in oname.lower():
                    oname = self.allDomains[currReg][1] + '; ' + domain.name
        oname = "; ".join(list(set(oname.split("; ")))) if oname is not None else oname
        return cdname, oname

    def noteAdd(self, domain, currReg):
        """merge notes of similar records"""
        if domain.note is not None:
            if self.allDomains[currReg][2] is None:
                return domain.note
            elif domain.note.lower() not in self.allDomains[currReg][2].lower() and \
                    self.allDomains[currReg][2] is not None:
                return self.allDomains[currReg][2] + '; ' + domain.note
            elif self.allDomains[currReg][2].lower() in domain.note.lower():
                return domain.note
            else:
                return self.allDomains[currReg][2]
        else:
            return self.allDomains[currReg][2]

    def cddAdd(self, domain, currReg):
        """merge cdd ids of similar records"""
        if self.allDomains[currReg][3] is None:
            return domain.cdd
        elif domain.cdd is not None and domain.cdd not in self.allDomains[currReg][3] and \
                domain.cdd not in self.allCDD:
            return self.allDomains[currReg][3] + '; ' + domain.cdd
        else:
            return self.allDomains[currReg][3]

    def addToExtID(self, extID, currentExt):
        """merge external ids (select one or join strings"""
        if currentExt is None:
            return extID
        elif extID is None:
            return currentExt
        else:
            return "; ".join(list(set(currentExt.split("; ") + extID.split("; "))))

