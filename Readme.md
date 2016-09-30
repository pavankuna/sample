# Agenda
    To Activate ILOM configured hosts in ASR manager


    Once ILOMS are configured with hosts, they are activated in ASRM as assets

# Functionality
    Supernet plays a key role is mapping the appropriate ASRM to ILOM

    ILOM supernet represents the region it belongs to. A pre defined file which represents the nearest ASRM to the region is used for mapping.

    ILOM is to be configured with the ASR details and then the ILOM is activated in the ASR.


# ILOM configuration
    ILOM needs the following parameters to be defined
        * destination
        * destination_port
        * level
        * snmp_version
        * type
        * community_or_username

# ASR activation
    ASR can activate a configured ILOM using following command
        * activate_asset -ip [ip address]

# INPUTS
    ASR and ILOM supernet file:
        List of supernet that ILOM belongs in a row and corresponding ASR that can be mapped in next row. File can be in .csv/.txt format

    ILOM host file:
        List of ILOMS configured host names

    Wallet:
        To enhance the security measures encrypted passwords are used rather than a plain text passwords.

        Two wallet files are required , one for storing ASR, Database, Grafana passwords and other for ILOM host passwords.

# OUTPUTS
    Following parameters are extracted and shown as resultant:
                * SHORTNAME
                * DOMAIN
                * OOB_HOSTNAME
                * SERIAL_NUMBER
                * MODEL
                * ERROR
                    -Ilom timeout error
                    -Ilom Authentication error
                    -Unable to connect to the port
                    -ASSET ACTIVATION FAILED
                    -ILOM configuration failed
                    -No ASR manager found
                * EVENT_TIME
                * ASR_SERVER
                * ASR_CONFIGURED
    No of hosts got activation success
    No of hosts got activation Failure
    No of hosts got activation Pending
# Tools
    Grafana: A graphical graph representation for number of hosts in success, failure, pending states.
    Database: All parameters mentioned in OUTPUTS section above are each columns in database.
              Additionaly JOBS is a table to represent the name of the user as well the machine name and a capture of the execution start time and end time is done.

# Metrics


















