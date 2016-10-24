#!/scratch/kedigac/python_2.7/bin/python
# Script to check Unsecure protocol status for HOST
#Author(s): Naga Sai Vosetti <naga.sai.vosetti@oracle.com>

import sqlite3
import multiprocessing as mp
import time
import sys
import os
import re
import paramiko
import signal
import socket
import html
import threading
import csv
import commands

def create_table(db_name,table_name,sql):
    with sqlite3.connect(db_name) as db:
        cursor = db.cursor()
        cursor.execute("select name from sqlite_master where name=?",(table_name,))
        result = cursor.fetchall()
        if len(result) == 1:
            cursor.execute("drop table if exists {0}".format(table_name))
            db.commit()
        cursor.execute(sql)
        db.commit()
         
def insert_data(values):
     with sqlite3.connect(db_name) as db:
         cursor = db.cursor()
         sql = "insert into Datacenter (Hostname, OS) values (?, ?)"
         cursor.execute(sql,values)
         db.commit()

class TimedOutExc(Exception):
    """
    Raised when a timeout happens
    """
#
# timeout(timeout), timeout exception raise decorator.
#
def timeout(timeout):
    """
    Return a decorator that raises a TimedOutExc exception
    after timeout seconds, if the decorated function did not return.
    """
    def decorate(f):
        def handler(signum, frame):
            raise TimedOutExc('Running for longer time than expected hence killing the seession.')
        def new_f(*args, **kwargs):
            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)
            result = f(*args, **kwargs)  # f() always returns, in this scheme
            signal.signal(signal.SIGALRM, old_handler)  # Old signal handler is restored
            signal.alarm(0)  # Alarm removed
            return result
        new_f.func_name = f.func_name
        return new_f
    return decorate


def get_portstatus(hostname,port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex((hostname,port))
    if result == 0:
        return True
    else:
        return False


#
# ping_check(), to check the ping status of the host.
#
def check_ping(hostname):
    if os.system("ping -c 1 "+ hostname + ">/dev/null 2>1") == 0:
        return True
    else:
        return False

@timeout(120)         
def check_rlogin(hostname):
    result = {'ERROR': None, 'output': {}}
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username='root', timeout=30)
    except Exception as e:
        err = "SSH_ISSUE"
        result['ERROR'] = "%s,%s"%(hostname,'SSH_Issue')
        return result
    try:
        stdin, stdout, stderr  = ssh.exec_command('uname', timeout=30)
        output4 = "".join(stdout.readlines()).strip()
        if output4:
            result['output']['OS'] = output4
    except:
        result['output']['OS'] = 'TIMEOUT'
    if result['output']['OS'] == 'Linux':
         try:
             stdin, stdout, stderr  = ssh.exec_command("cat /etc/redhat-release |awk '{print $7}'", timeout=30)
             output5 = stdout.readlines()
             result['output']['OS_Version'] = output5
         except:
             result['output']['OS_Version'] = 'TIMEOUT'
    if result['output']['OS'] != 'Linux':
         ['output']['OS_Version'] = result['output']['OS']
    ssh.close()
    return result

def worker(hostname):
    try:
        if not check_ping(hostname):
            err = "PING_ISSUE"
            ping1 = "PING_Failed"
            return "%s,%s,%s,%s,%s,%s,%s"% (hostname,ping1,err,err,err,err,err)
        else:
            result = {}
            try:
                output_win =  get_portstatus(hostname,3389)
                if output_win:
                    win = "Windows"
                    return "%s,%s"% (hostname,win)
                else:
                    result = check_rlogin(hostname)
            except Exception as e:
               #result['ERROR'] = 'Exeuction timeout'
               result['ERROR'] =  '%s,%s'%(hostname,"Execution Timeout")
            if result['ERROR']:
                return result['ERROR']
            else:
                if result['output']['OS'] == 'Linux':
                    return "%s,%s"% (hostname,result['output']['OS_Version'])
                else:
                    return "%s,%s"% (hostname,result['output']['OS_Version'])
    except Exception, e:
        err="error"
        return "%s,%s"%(hostname,e)



result_list = []
Datacenter = []
def log_result(result):
     lock.acquire()
     Datacenter = result.split(",")
     if len(Datacenter) == 2:
         insert_data(Datacenter)
     lock.release()

def apply_async_with_callback(HOST_LIST,THREAD_COUNT):
    #pool = mp.Pool()
    pool = mp.Pool(processes=THREAD_COUNT)
    for i in HOST_LIST:
        pool.apply_async(worker, args = (i.strip(), ), callback = log_result)
    pool.close()
    pool.join()
    #for i in result_list:
    #   print i
    
def connection_db():
    con = sqlite3.connect('/scratch/nagasai/rlogin.db')
    with con:    
        cur = con.cursor()    
        cur.execute("select Datacenter.Hostname, OS, Cluster, Rlogin, Telnet, Rsh, Rexec, Location, Service, Owner from Datacenter inner join Datacollection on Datacollection.Hostname = Datacenter.Hostname")
        col_names = ["Hostname", "OS", "Cluster", "Rlogin", "Telnet", "Rsh", "Rexec", "Location", "Service", "Owner"]
        rows = cur.fetchall()
        print >> writer, ','.join(col_names)
        for i in rows:
            print >> writer, ','.join([str(x) for x in i])
        print >> html_log_fd,'<html>'
        print >>html_log_fd,'<head>'
        print >>html_log_fd,'<title>Protocol Status Page</title>'
        print >>html_log_fd,'<link rel="stylesheet" href="style.css">'
        print >>html_log_fd,'</head>'
        print >>html_log_fd,'<body>'
        print >>html_log_fd,'<div class="header">Protocol Status Page</div>'
        print >> html_log_fd,'<br> </br>'
        print >> html_log_fd,'<br> </br>'
        print >> html_log_fd,'<u><b>Protocol Output:</b></u>'
        print >> html_log_fd,'<br> </br>'
        h = html.HTML()
        t = h.table(border='1')
        r = t.tr
        for i in col_names:
            r.td(i)
        for row in rows:
            r = t.tr
            for i in row:
                if i:
                    r.td(i)
                else:
                    i='Null'
                    r.td(i)
        print >> html_log_fd,t
        print >> html_log_fd,'<br> </br>'
        print >> html_log_fd,'<br> </br>'
        print >> html_log_fd,'If you found any errors in the report email: <a href="url">naga.sai.vosetti@oracle.com</a>'
        print >>html_log_fd,'</body>'
        print >>html_log_fd,'</html>'


        html_log_fd.close()
        print >> html_log1_fd,'<html>'
        print >>html_log1_fd,'<head>'
        print >>html_log1_fd,'<title>Protocol Summary Page</title>'
        print >>html_log1_fd,'<link rel="stylesheet" href="style.css">' 
        print >>html_log1_fd,'</head>'
        print >>html_log1_fd,'<body>'
        print >>html_log1_fd,'<div class="header">Protocol Summary Page</div>'
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,'<br> </br>'
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname")
        scanned_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where Os='PING_Failed'")
        ping_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where Os='SSH_Issue'")
        ssh_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where Os='TIMEOUT' or Os='Execution Timeout'")
        time_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where Os='Linux' or Os='SunOS'")
        supp_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where Os='AIX' or Os='Darwin' or Os='FreeBSD' or Os='HP-UX' or Os='VMkernel' or Os='Windows'")
        unsupported_count=cur.fetchone()[0]
        cur.execute("select DISTINCT Os from Datacenter where Os Not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Os in ('AIX','Darwin','FreeBSD','HP-UX','Linux','SunOS','VMkernel','Windows')")
        unique_os = cur.fetchall()
        unique_os_count = []
        unique_os_count.append(['OS','Total Count','Rlogin','Telnet','Rsh','Rexec'])
        for k in unique_os:
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os=?",(k))
            T_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os=? and Rlogin='Yes'",(k))
            Rlogin_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os=? and Telnet='Yes'",(k))
            Telnet_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os=? and Rsh='Yes'",(k))
            Rsh_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os=? and Rexec='Yes'",(k))
            Rexec_count=cur.fetchone()[0]
            k=k[0]
            unique_os_count.append([k,T_count,Rlogin_count,Telnet_count,Rsh_count,Rexec_count])
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname")
        T1_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rlogin='Yes'")
        Rlogin_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Telnet='Yes'")
        Telnet_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rsh='Yes'")
        Rsh_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where os  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rexec='Yes'")
        Rexec_total=cur.fetchone()[0]
        unique_os_count.append(['Total',T1_count,Rlogin_total,Telnet_total,Rsh_total,Rexec_total])

        cur.execute("select DISTINCT Service from Datacollection")
        unique_service = cur.fetchall()
        unique_service_count = []
        unique_service_count.append(['Service Area','Total Count','Rlogin','Telnet','Rsh','Rexec'])
        for k in unique_service:
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service=?",(k))
            T_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service=? and Rlogin='Yes'",(k))
            Rlogin_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service=? and Telnet='Yes'",(k))
            Telnet_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service=? and Rsh='Yes'",(k))
            Rsh_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service=? and Rexec='Yes'",(k))
            Rexec_count=cur.fetchone()[0]
            k=k[0]
            unique_service_count.append([k,T_count,Rlogin_count,Telnet_count,Rsh_count,Rexec_count])
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT')")
        T1_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rlogin='Yes'")
        Rlogin_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Telnet='Yes'")
        Telnet_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rsh='Yes'")
        Rsh_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where service  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rexec='Yes'")
        Rexec_total=cur.fetchone()[0]
        unique_service_count.append(['Total',T1_count,Rlogin_total,Telnet_total,Rsh_total,Rexec_total])

        cur.execute("select DISTINCT location from Datacollection where location Not in ('')")
        unique_location = cur.fetchall()
        unique_location_count = []
        unique_location_count.append(['Region Name','Total Count','Rlogin','Telnet','Rsh','Rexec'])
        for k in unique_location:
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location=?",(k))
            T_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location=? and Rlogin='Yes'",(k))
            Rlogin_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location=? and Telnet='Yes'",(k))
            Telnet_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location=? and Rsh='Yes'",(k))
            Rsh_count=cur.fetchone()[0]
            cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location=? and Rexec='Yes'",(k))
            Rexec_count=cur.fetchone()[0]
            k=k[0]
            unique_location_count.append([k,T_count,Rlogin_count,Telnet_count,Rsh_count,Rexec_count])
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT')")
        T1_count=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rlogin='Yes'")
        Rlogin_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Telnet='Yes'")
        Telnet_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location  not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rsh='Yes'")
        Rsh_total=cur.fetchone()[0]
        cur.execute("select count(*) from Datacollection inner join Datacenter on Datacollection.Hostname=Datacenter.Hostname where location not in ('Execution Timeout','PING_Failed','SSH_Issue','TIMEOUT') and Rexec='Yes'")
        Rexec_total=cur.fetchone()[0]
        unique_location_count.append(['Total',T1_count,Rlogin_total,Telnet_total,Rsh_total,Rexec_total])

        print >> html_log1_fd,'<u><b>OS:</b></u>'
        print >> html_log1_fd,'<br> </br>'
        v = html.HTML()
        t = v.table(border='1')
        for h in range(len(unique_os_count)):
            r=t.tr
            for p in unique_os_count[h]:
                r.td(str(p))
        print >> html_log1_fd,t
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,'<u><b>Service Area:</b></u>'
        print >> html_log1_fd,'<br> </br>'
        v = html.HTML()
        t = v.table(border='1')
        for h in range(len(unique_service_count)):
            r=t.tr
            for p in unique_service_count[h]:
                r.td(str(p))
        print >> html_log1_fd,t
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,'<u><b>Region Name:</b></u>'
        print >> html_log1_fd,'<br> </br>'
        v = html.HTML()
        t = v.table(border='1')
        for h in range(len(unique_location_count)):
            r=t.tr
            for p in unique_location_count[h]:
                r.td(str(p))
        print >> html_log1_fd,t
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,"Total Number of hosts that are SCANNED: %s" %(scanned_count)
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,"Total Number of hosts that have PING FAILURE: %s" %(ping_count)
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,"Total Number of hosts that have SSH ISSUE: %s" %(ssh_count)
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,"Total Number of hosts that have TIMEOUT: %s" %(time_count)
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,"Total Number of hosts LINUX and SUN OS: %s" %(supp_count)
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,"Total Number of hosts UNSUPPORTED: %s" %(unsupported_count)
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,'If you found any errors in the report email: <a href="url">naga.sai.vosetti@oracle.com</a>'
        print >> html_log1_fd,'<br> </br>'
        print >> html_log1_fd,'<div style="text-align: center;">'
        print >> html_log1_fd,'<form method="get" action="rlogin.csv">'
        print >> html_log1_fd,'<button type="submit">Download Result file!</button>'
        print >> html_log1_fd,'</form>'
        print >> html_log1_fd,'</div>'
        print >>html_log1_fd,'</body>'
        print >>html_log1_fd,'</html>'


if __name__ == "__main__":
    lock = threading.Lock()
    db_name = "/scratch/nagasai/OS.db"
    sql = """create table Datacenter
              (Hostname text,
              OS text,
              primary key(Hostname))"""
    create_table(db_name,"Datacenter",sql)
    THREAD_COUNT = 100
    input = '/scratch/nagasai/OSlist'
    HOST_LIST = list()
    if os.path.isfile(input):
        HOST_LIST = open(input,'r').readlines()
    else:
        HOST_LIST.append(input)

    if len(HOST_LIST) == 1:
        THREAD_COUNT = 1
    elif len(HOST_LIST) < 100:
        THREAD_COUNT = len(HOST_LIST)
    apply_async_with_callback(HOST_LIST,THREAD_COUNT)
    #connection_db()
