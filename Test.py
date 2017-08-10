import ncs
import socket

if __name__ == '__main__':
    with ncs.maapi.Maapi() as m:
        with ncs.maapi.Session(m, 'ncsadmin', 'python', groups=['ncsadmin']):

            with m.start_write_trans() as t:
                root = ncs.maagic.get_root(t)
                for ogtyp in root.devices.device["asa-netsim-1"].config.asa__object_group:
                    for og in root.devices.device["asa-netsim-1"].config.asa__object_group[ogtyp]:
                        del root.devices.device["asa-netsim-1"].config.asa__object_group[ogtyp][og.id]

                t.apply()


            with m.start_write_trans() as t:
                root = ncs.maagic.get_root(t)
                for acl in root.devices.device["asa-netsim-1"].config.asa__access_list.access_list_id:
                    del root.devices.device["asa-netsim-1"].config.asa__access_list.access_list_id[acl.id]

                t.apply()
        
