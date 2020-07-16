import re
from sqlite3 import connect
from Director import Director
from InterproCollector import InterProBuilder
import pandas as pd


class DomainOrganizer:

    def __init__(self, download=False):
        self.allDomains = dict()  # keys are id, vals sre tuple combined from Domain object info
        self.internalID = 0
        self.allExt = dict()
        self.allNames = dict()
        self.allCDD = dict()
        director = Director()
        self.Interpro = InterProBuilder()
        director.setBuilder(self.Interpro)
        director.collectFromSource(download=download)

    def collectDatafromDB(self, dbname='DB_merged.sqlite'):
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
        currReg = None
        existExt = [None] * 5
        external = ['cdd', 'pfam', 'smart', 'tigrfams', 'interpro']
        if domain.extID is None:
            return None
        elif domain.extType not in external:
            return None
        identify = self.Interpro.AllDomains.loc[
            self.Interpro.AllDomains[domain.extType].str.contains(domain.extID, na=False)]
        ind = identify.index.values[0] if len(identify) != 0 else None
        if self.Interpro.AllDomains.loc[ind, "Type"] != "domain":  # if the record is family and not single domain
            return None
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
        self.allDomains[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
        self.allExt[domain.extID] = currReg
        self.allNames[domain.name] = currReg
        self.allCDD[domain.cdd] = currReg
        return currReg

    def mainNameOtherName(self, domain, currReg):
        cdname = self.allDomains[currReg][0]
        oname = self.allDomains[currReg][1]
        if domain.extType == 'interpro':
            cdname = domain.name
        elif domain.name is not None:
            if self.allDomains[currReg][0] and self.allDomains[currReg][1] is not None:
                if domain.name.lower() not in self.allDomains[currReg][0].lower() and \
                        domain.name.lower() not in self.allDomains[currReg][1].lower():
                    oname = self.allDomains[currReg][1] + '; ' + domain.name
                else:
                    oname = self.allDomains[currReg][1]
            else:
                oname = domain.name
        return cdname, oname

    def noteAdd(self, domain, currReg):
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
        if self.allDomains[currReg][3] is None:
            return domain.cdd
        elif domain.cdd is not None and domain.cdd not in self.allDomains[currReg][3] and \
                domain.cdd not in self.allCDD:
            return self.allDomains[currReg][3] + '; ' + domain.cdd
        else:
            return self.allDomains[currReg][3]

    def addToExtID(self, extID, currentExt):
        if currentExt is None:
            return extID
        elif extID is None:
            return currentExt
        else:
            return "; ".join(list(set(currentExt.split("; ") + extID.split("; "))))
