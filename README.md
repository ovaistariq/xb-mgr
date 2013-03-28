XtraBackup Backup Manager
=========================

XtraBackup Backup Manager (xb-mgr) is a backup manager for backing up MySQL data. It uses Percona XtraBackup tool (http://www.percona.com/doc/percona-xtrabackup/intro.html) to backup a MySQL instance. xb-mgr is fairly simple to use and configure. It supports ini style configuration files that can be used to configure backups for remote MySQL instances. xb-mgr supports full backups as well as incremental backups, and is designed to work in the following way. The user specifies which day of the week full backup should be taken, suppose that is Sunday, then every Sunday a full backup is taken once, and every other day incremental backups are taken. xb-mgr also supports multiple backups per day. For example you can setup xb-mgr to run every 8 hour each day via CRON. Note that on the day when full backup is taken, even if you run xb-mgr multiple times, it will still take only a single full backup on that day, and remaining backups will be incremental. xb-mgr also keeps a compressed copy of a fully prepared backup available to make the process of restoring from backups efficient. xb-mgr supports keeping multiple copies of prepared and compressed backups available. This is configurable, for example you can configure to only have 1 prepared backup available, and the latest prepared backup will always be available. xb-mgr also supports logging to a log file as well as sending an email with the log of the backup run to a specified email address.

Running xb-mgr is as simple as executing a single script. Suppose xb-mgr is installed at /usr/local/xb-mgr, then you can run xb-mgr as follows:  
/usr/local/xb-mgr/backup_manager.py

Package Requirements and Dependencies
=====================================
xb-mgr is written in Python 2.6 so if you an older version of Python running you must upgrade to Python 2.6.

Please make sure that you meet the following requirements on the machine which will be hosting xb-mgr.

In addition to Python 2.6, you would need the following packages installed:  
    + **ansible** - You can read more about installing ansible and its dependencies here: http://ansible.github.com/gettingstarted.html  
    + **percona-xtrabackup** - You must have version >= 2.0 installed for it to work, because xb-mgr uses the new streaming format 'xbstream' introduced in percona-xtrabackup >= 2.0. You must make sure that the tool xbstream is available at location /usr/bin/xbstream and that the tool innobackupex is available at the location /usr/bin/innobackupex. Typical installs of percona-xtrabackup do install the tools xbstream and innobackupex inside /usr/bin.  
    + **qpress** - This package is available here: http://www.quicklz.com/ You must make sure that qpress is available at the location /usr/bin/qpress.  
    + **MySQL-server** - xb-mgr relies on at least the same major version of MySQL server installed, as is the version on the remote MySQL server which will be backed up. You must make sure that mysqld is available at /usr/sbin/mysqld.  
    + **MySQL-client** - xb-mgr relies on the MySQL client package being installed, because it uses the tool mysqlcheck to check the backed up data after taking a backup. You must make sure that mysqlcheck is available at /usr/bin/mysqlcheck.  
    + **MySQL-shared**  
    + **MySQL-shared-compat**  

In addition to the above the remote hosts that will be backed up must have the following packages installed:  
    + **percona-xtrabackup** - You must have version >= 2.0 installed for it to work, because xb-mgr uses the new streaming format 'xbstream' introduced in percona-xtrabackup >= 2.0. You must make sure that the tool xbstream is available at location /usr/bin/xbstream and that the tool innobackupex is available at the location /usr/bin/innobackupex. Typical installs of percona-xtrabackup do install the tools xbstream and innobackupex inside /usr/bin.  
    + **qpress** - This package is available here: http://www.quicklz.com/ You must make sure that qpress is available at the location /usr/bin/qpress.  

You must have noticed that some executatbles used by xb-mgr are required to be at specific location. I intend on removing this restriction in a future version.

Before continuing on with the rest of the sections, let me introduce two keywords that I will be using in this section:  
    + **manager-host** - This is the machine that is hosting xb-mgr  
    + **remote-host** - This is the remote machine running the MySQL server that is to be backed up  

SSH Authentication and Authorization
====================================
For xb-mgr to run you must make sure that manager-host can connect to remote-host via SSH and vice-versa. This might mean opening up port 22, at the moment xb-mgr only supports SSH connections via port 22. Currently, xb-mgr supports password-less SSH authentication only, which means that you must have public/private key pairs setup, so that publickey authentication can be used.

Configuration
=============
xb-mgr uses ini-style configuration files. The configuration file is located in the conf directory inside the xb-mgr directory. So if you have xb-mgr at location /usr/local/xb-mgr, the configuration file will be available at /usr/local/xb-mgr/conf/backup.conf. 

The xb-mgr configuration file has a section called 'default' which has general options pertaining to xb-mgr. The configuration file also has remote-host specific section, which is called after the hostname. Moreover, the options defined in remote-host section override the options defined in the default section.

xb-mgr supports the following general configuration options that can be specified in the default section:  
    + mysql_user - This is the MySQL user that will be used by xb-mgr during the backup process. The user must exist on the remote-host, and should have the following privileges:  
	- RELOAD  
	- LOCK TABLES  
	- REPLICATION CLIENT  
	- SUPER  
    + mysql_password - This is the password for the MySQL user  
    + ssh_user - This is the SSH user that will be used to connect from manager-host to remote-host and from remote-host to manager-host. This user must be able to perform operations on the MySQL datadir at remote-host, and must also be able to perform operations on the directory on manager-host where backups will be stored  
    + backup_manager_host - The IP of the manager-host  
    + remote_backup_cmd - xb-mgr installs a helper script on the remote host to aid in the backup process. This config option specifies the location where this helper script should be installed  
    + root_dir - The root directory of xb-mgr install, for example if xb-mgr is installed in /usr/local/backup-manager, then the root_dir will be /usr/local/backup-manager  
    + backup_dir - The root directory where backups taken by xb-mgr are stored. Within this directory xb-mgr creates separate directories for each remote-host to be backed up, see the section **Backup Directory Structure** for details  
    + log - The path to the log file where xb-mgr will write all messages generated during the backup run  
    + pid - The path to the file where xb-mgr will write its pid  
    + retain_days - The number of days upto which the backups must be retained. xb-mgr makes sure that you can always go back upto retain_days days in the past, sometimes this would mean storing backups that are more than retain_days old, this is because incremental backups always need full backup to be able to be restored upto the day when the incremental backup was taken. Note that backups are removed only when the current run of xb-mgr was successfull  
    + retain_num_ready_backups - The number of prepared-compressed backups that must be retained. After every successful backup run xb-mgr creates a prepared-compressed backup that is read to be restored. xb-mgr keeps at most retain_num_ready_backups copies of prepared-compressed backup. When the number of prepared-compressed backups exceeds the value of retain_num_ready_backups, oldest prepared-compressed backups are removed. Note that the removal of backups only takes place when the current run of xb-mgr was successfull, this is to make sure that the last prepared-compressed backup is always available  
    + error_email_recipient - A comma-separated list of email addresses to which email will be sent after xb-mgr run. This can also be a single email address.  

All the options defined above can also be specified in the remote-host specific section, and they will override the values of options defined in the default section. The remote-host specific section has one extra option:  
    + hostname - The hostname of the remote-host that is to be backed up. Currently xb-mgr cannot work with IP addresses of remote-host, so you must specify the hostname and make sure that the hostname resolves either via /etc/hosts file or via DNS resolution  

Note that you must have separate section for each remote-host. Let me show you an example configuration file:  

---
    [default]
    mysql_user          = backup_man
    mysql_password      = some_pass
    ssh_user            = root
    backup_manager_host = root@10.10.1.1
    remote_backup_cmd   = /usr/local/xb-mgr/bin/backup_local
    full_backup_day     = Sunday
    root_dir            = /usr/local/xb-mgr
    backup_dir          = /backup
    log                 = /var/log/xb-mgr/backup_manager.log
    pid                 = /var/run/xb-mgr.pid
    retain_days         = 7
    retain_num_ready_backups = 1
    error_email_recipient = ovaistariq@gmail.com

    [db1]
    hostname    = db1
    log         = /var/log/xb-mgr/db1.log
---

Note that we have two sections above, one is the default section which consists of general options. While the second section 'db1' is specific to the remote-host 'db1'. Note that we have specified the hostname in the section db1, which is what will be used to connect tothe remote-host, also see how we have overridden the value of config variable 'log'.

Remote hosts and Ansible Configuration
======================================
As have already been mentioned that xb-mgr depends on Ansible. xb-mgr uses the ansible python modules to execute commands on remote-hosts. But before ansible can talk to a remote-host, that remote-host must be specified in the ansible hosts file. The ansible hosts file is located at /etc/ansible/hosts So before you add a new remote-host to the xb-mgr configuration file, make sure its already specified in the file /etc/ansible/hosts either as part of a group of hosts or as a standalone host. The hostname in the file /etc/ansible/hosts must match the name of the host in the xb-mgr configuration file. For example in the sample configuration file above, there is a host 'db1', this host must also be defined in the file /etc/ansible/hosts as 'db1'.

Backup Directory Structure
==========================
xb-mgr stores all backups in the directory specified by the option **backup_dir**. xb-mgr creates separated directories for each individual remote-hosts. Suppose backup_dir=/backup and the remote-hosts are 'db1' and 'db2', then the directory structure will look like the following:

    * /backup/ - The root backup directory
	* db1/ - The backup directory corresponding to the remote-host 'db1'
	    * full/ - The directory that will hold full backups
	    * incremental/ - The directory that will hold incremental backups
	    * ready/ - The directory that will hold prepared-compressed backups. You would mostly be concerned with this directory, as it would stored the prepared-compressed backup that you would restore
	* db2/ - The backup directory corresponding to the remote-host 'db2'
            * full/ - The directory that will hold full backups
            * incremental/ - The directory that will hold incremental backups
            * ready/ - The directory that will hold prepared-compressed backups. You would mostly be concerned with this directory, as it would stored the prepared-compressed backup that you would restore
	    * prepare/ - This is a temporary directory that xb-mgr creates during the backup run

The directories *full* and *incremental* contain timestamped directories that hold files:
    * backup.xbstream - This is a compressed and archived backup that is not prepared
    * xtrabackup_checkpoints - This is a file that holds InnoDB LSN information that is internally used by xb-mgr to manage backups

The directory *ready* conatains timestamped compressed files. Each file is a compressed-prepared backup ready to be used to restore. The compressed file is created using qpress.

Examples
========
All examples below assume the configuration used is the sample configuration file shown in the *Configuration* section.

Do a backup of remote-host 'db1' once:

    /usr/local/xb-mgr/backup_manager.py

Do backup of remote-host 'db1' every 8 hours using CRON:

    Add the following line to /etc/crontab:
    * */8 * * * root /usr/local/xb-mgr/backup_manager.py > /dev/null 2>&1

Add a new remote-host 'db2' to be backed up:

    Make sure SSH works from manager-host to db2 and vice versa
    Add db2 to the file /etc/ansible/hosts
    Add the following section to the file /usr/local/xb-mgr/conf/backup.conf:
    [db2]
    hostname    = db2
    log         = /var/log/xb-mgr/db2.log

