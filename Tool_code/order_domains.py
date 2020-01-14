# -*- coding: utf-8 -*-
"""
Created on Thu Dec  5 09:41:38 2019

@author: galozs
"""
import re
 #external ID list is built as: ['cd','cl','pfam','smart','nf','cog','kog','prk','tigr']
 #list inside dTypeDict: (name, other names,  description, CDD_id, 'cd','cl','pfam','smart','nf','cog','kog','prk','tigr')
def order_domains(region, dTypeDict, dTypeID, dExt, dNames, dCDD):
    external = ['cd','cl','pfam','smart','nf','cog','kog','prk','tigr','other']
    extIDs = [None, None, None, None, None, None, None, None, None, None]
    oname = None
    cdname = None
    pref = None
    currReg = None
    for pref in range(len(external)):
        if region[4] == None:
            if region[3].lower().startswith(external[pref]):
                currExt = region[3]
            else:
                currExt = region[4]
            break
        elif "Provisional" in region[4] and re.sub(r'\d+$','',region[2]) in ['CHL', 'MTH', 'PHA', 'PLN', 'PTZ', 'PRK']:
            currExt = region[2]
            break
        else:
            currExt = region[4]       
            break
    for pref in range(len(external)):
        if currExt == None:
            pref = 9
            break
        elif currExt.lower().startswith(external[pref]):
            break 
        elif re.sub(r'\d+$','',currExt) in ['CHL', 'MTH', 'PHA', 'PLN', 'PTZ', 'PRK']:
            pref = 7
            break
        else:
            pref = 9
    if currExt != None and currExt not in dExt:
        #print('extID not  exist')
        if region[2] not in dNames:
            #print('name exist 1')
            if region[5] == None or region[5] not in dCDD:
                dTypeID += 1
                extIDs[pref] = currExt
                existExt = extIDs
                cdname = region[2]
                oname = region[2]
                currReg = dTypeID
                #dTypeDict[currReg] = (cdname, oname, region[3], region[5],) + tuple(extIDs)
                ndesc = region[3]
                ncdd = region[5]
                dExt[currExt] = currReg
                dNames[region[2]] = currReg
                dCDD[region[5]] = currReg
            elif region[5] != None and region[5] in dCDD:
                existExt = list(dTypeDict[dCDD[region[5]]][4:])
                currReg = dCDD[region[5]]
                if existExt[pref] == None or currExt in existExt[pref]:
                    existExt[pref] = currExt
                elif existExt[pref].startswith(re.sub(r'\d+$','', currExt)):
                    existExt[pref] = existExt[pref] + '; ' + currExt
                else:
                    raise ValueError('exernal id not in correct location!')
                if region[3].lower() not in dTypeDict[currReg][2].lower() and dTypeDict[currReg][2].lower() not in region[3].lower():
                    ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
                else: ndesc = dTypeDict[currReg][2]
                cdname = dTypeDict[currReg][0]
                oname = dTypeDict[currReg][1] 
                if pref == 0:
                    cdname = region[2]
                elif region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                    oname =  dTypeDict[currReg][1] + '; ' + region[2]
                ncdd = str(dTypeDict[currReg][3])
                #dTypeDict[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
                dNames[region[2]] = currReg
                dExt[currExt] = currReg
        elif region[2] in dNames:
            #print('name exist 2')
            existExt = list(dTypeDict[dNames[region[2]]][4:])
            currReg = dNames[region[2]]
            if existExt[pref] == None or currExt in existExt[pref]:
                existExt[pref] = currExt
            elif existExt[pref].startswith(re.sub(r'\d+$','', currExt)):
                existExt[pref] = existExt[pref] + '; ' + currExt
            else:
                raise ValueError('exernal id not in correct location!')
            if region[5] != None and region[5] not in str(dTypeDict[currReg][3]) and region[5] not in dCDD:
                ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
                dCDD[region[5]] = currReg
            else: ncdd = str(dTypeDict[currReg][3])
            if region[3] != None and region[3] not in dTypeDict[currReg][2]:
                ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
            else: ndesc = dTypeDict[currReg][2]
            cdname = dTypeDict[currReg][0]
            oname = dTypeDict[currReg][1] 
            if pref == 0:
                cdname = region[2]
            elif region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                oname =  dTypeDict[currReg][1] + '; ' + region[2]
            #dTypeDict[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)                              
            dExt[currExt] = currReg
    elif currExt in dExt and currExt != None:
        #print('extID exist')
        currReg = dExt[currExt]
        if region[2].lower() == dTypeDict[currReg][0].lower() or region[2].lower() in dTypeDict[currReg][1].lower():
            if region[5] != None and region[5] not in str(dTypeDict[currReg][3]):
               ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
               dCDD[region[5]] = currReg
            else: ncdd = str(dTypeDict[currReg][3])
            if region[3] != None and region[3] not in dTypeDict[currReg][2]:
                ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
            else: ndesc = dTypeDict[currReg][2]
            existExt = dTypeDict[currReg][4:]
            cdname = dTypeDict[currReg][0]
            oname = dTypeDict[currReg][1]
            if pref == 0:
                cdname = region[2]
            elif region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                oname =  dTypeDict[currReg][1] + '; ' + region[2]
            #dTypeDict[currReg] = (reg[2], ndesc, ncdd,) + extIDs  
        elif re.sub(r'[_ ]\d+$','', region[2]) == re.sub(r'[_ ]\d+$','', dTypeDict[currReg][0]):
            if region[5] != None and region[5] not in str(dTypeDict[currReg][3]):
               ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
               dCDD[region[5]] = currReg
            else: ncdd = str(dTypeDict[currReg][3])
            if region[3] != None and region[3] not in dTypeDict[currReg][2]:
                ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
            else: ndesc = dTypeDict[currReg][2]
            cdname = re.sub(r'[_ ]\d+$','',dTypeDict[currReg][0])
            oname = dTypeDict[currReg][1] 
            if region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                oname =  oname + '; ' + region[2]
            existExt = dTypeDict[currReg][4:]
            #dTypeDict[dExt[currExt]] = (namenonum, ndesc, ncdd,) + extIDs  
        else:
            #print('here 6')
            if region[5] != None and region[5].lower() not in str(dTypeDict[currReg][3]).lower():
               ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
               dCDD[region[5]] = currReg
            else: ncdd = str(dTypeDict[currReg][3])
            if region[3] != None and region[3] not in dTypeDict[currReg][2]:
                ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
            else: ndesc = dTypeDict[currReg][2]
            existExt = dTypeDict[currReg][4:]
            cdname = dTypeDict[currReg][0]
            oname = dTypeDict[currReg][1] 
            if pref == 0:
                cdname = region[2]
            elif region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                oname =  dTypeDict[currReg][1] + '; ' + region[2]
            #dTypeDict[dExt[currExt]] = (dTypeDict[dExt[currExt]][0], ndesc, ncdd,) + extIDs  
    elif currExt == None:
        #print('no currext')
        if region[2] in dNames: 
            currReg = dNames[region[2]]
            existExt = list(dTypeDict[currReg][4:])
            if region[5] != None and region[5] not in str(dTypeDict[currReg][3]) and region[5] not in dCDD:
                ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
                dCDD[region[5]] = currReg
            else: ncdd = str(dTypeDict[currReg][3])
            if region[3] != None and region[3] not in dTypeDict[currReg][2]:
                ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
            else: ndesc = dTypeDict[currReg][2]
            cdname = dTypeDict[currReg][0]
            oname = dTypeDict[currReg][1] 
                #dTypeDict[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)                              
        else:
            if region[5] not in dCDD and region[5] != None:
                dTypeID += 1
                ncdd = region[5]
                oname = region[2]
                cdname = region[2]
                currReg = dTypeID
                #dTypeDict[currReg] = (cdname, oname, region[3], region[5],) + tuple(extIDs)
                ndesc = region[3]
                dNames[region[2]] = currReg
                dCDD[region[5]] = currReg
                existExt = extIDs
            elif region[5] != None:
                currReg = dCDD[region[5]]
                if re.sub(r'[_ ]\d+$','', region[2]) == re.sub(r'[_ ]\d+$','', dTypeDict[currReg][0]) or re.sub(r'[_ ]\d+$','', region[2]) == re.sub(r'[_ ]\d+$','', dTypeDict[currReg][1]):
                    if region[3] not in dTypeDict[currReg][2]:
                        ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
                    else: ndesc = dTypeDict[currReg][2]
                    if region[5] not in str(dTypeDict[currReg][3]) and region[5] not in dCDD:
                        ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
                        dCDD[region[5]] = currReg
                    else: ncdd = str(dTypeDict[currReg][3])
                    cdname = re.sub(r'[_ ]\d+$','',dTypeDict[currReg][0])
                    oname = dTypeDict[currReg][1]
                    if region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                        oname =  oname + '; ' + region[2]
                    existExt = list(dTypeDict[currReg][4:])
                    dNames[region[2]] = currReg
                else:
                    if region[3] != None and region[3] not in dTypeDict[currReg][2]:
                        ndesc =  dTypeDict[currReg][2] + '; ' + region[3]
                    else: ndesc = dTypeDict[currReg][2]
                    if region[5] not in str(dTypeDict[currReg][3]) and region[5] not in dCDD:
                        ncdd = str(dTypeDict[currReg][3]) + '; ' + region[5]
                        dCDD[region[5]] = currReg
                    else: ncdd = str(dTypeDict[currReg][3])
                    cdname = dTypeDict[currReg][0]
                    oname = dTypeDict[currReg][1]
                    if region[2].lower() not in dTypeDict[currReg][0].lower() and region[2].lower() not in dTypeDict[currReg][1].lower():
                        oname =  oname + '; ' + region[2]
                    existExt = list(dTypeDict[currReg][4:])
                    dNames[region[2]] = currReg
    else:
        raise ValueError('ERROR done: region: ' + str(region))
    try:
        dTypeDict[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
    except Exception:
        raise Exception(str(region))
    return currReg, currExt, dTypeDict, dTypeID, dExt, dNames, dCDD