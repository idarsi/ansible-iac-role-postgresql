# Patroni with an external etcd cluster

This practical example configures three PostgreSQL hosts as one Patroni
cluster, using an already-provisioned three-member etcd v3 cluster. The role
installs and configures PostgreSQL and Patroni; it does **not** provision
external etcd, its PKI, firewall rules, or DNS. Provision the etcd client
certificate materials on every PostgreSQL host before running this playbook.
The paths below are under `/etc/etcd/`, as expected by the role.

Store the shared blueprint in group variables so every PostgreSQL member sees
the identical cluster definition. Each playbook sets `state` as a role
parameter, so multiple playbooks can reuse this inventory while selecting
different operations. `members[].host` values must exactly match the
corresponding Ansible `inventory_hostname`; each `instance` and `name`
identifies a local instance and unique Patroni member.

## Inventory

```yaml
---
all:
  children:
    postgres_patroni:
      hosts:
        pg01.example.net:
        pg02.example.net:
        pg03.example.net:
      vars:
        iac_blueprint:
          postgresql:
            - version: 17
              clusters:
                - name: production
                  provider: patroni
                  dcs:
                    provider: etcd3
                    endpoints:
                      - "https://etcd01.example.net:2379"
                      - "https://etcd02.example.net:2379"
                      - "https://etcd03.example.net:2379"
                    etcd:
                      tls:
                        enabled: true
                        client:
                          ca_file: "/etc/etcd/pki/ca.crt"
                          cert_file: "/etc/etcd/pki/client.crt"
                          key_file: "/etc/etcd/pki/client.key"
                  patroni:
                    postgresql:
                      superuser_password: "{{ vault_patroni_superuser_password }}"
                    replication_password: "{{ vault_patroni_replication_password }}"
                    pg_hba:
                      - "local all all peer"
                      - "hostssl all postgres 10.20.30.0/24 scram-sha-256"
                      - "hostssl replication replicator 10.20.30.0/24 scram-sha-256"
                    restapi:
                      authentication:
                        username: patroni_api
                        password: "{{ vault_patroni_api_password }}"
                  members:
                    - host: pg01.example.net
                      instance: main
                      name: production-pg01
                    - host: pg02.example.net
                      instance: main
                      name: production-pg02
                    - host: pg03.example.net
                      instance: main
                      name: production-pg03
              instances:
                - name: main
                  cluster: production
                  configuration:
                    listen_addresses: "*"
```

Replace the sample subnet with the narrowly scoped client and member network
that contains all Patroni member addresses and intended clients, so replication
is permitted. The sample uses `hostssl` rules and SCRAM authentication; ensure
clients are configured for TLS. Patroni's REST
API defaults to the inventory host address and port 8008, and its generated
allowlist is restricted to declared cluster members unless you configure an
explicit allowlist. Restrict that API at the network layer as well.

Keep the three credential variables encrypted with Ansible Vault. Ensure
firewall policy permits PostgreSQL traffic on TCP/5432 between intended
clients and members, Patroni API TCP/8008 only from authorized operators and
cluster members, and etcd client TCP/2379 from each PostgreSQL host to all
configured etcd endpoints. DNS names must resolve consistently from all
members. Manage etcd peer traffic and its firewall separately on the etcd
hosts.

The external etcd service must already be healthy, have quorum, and accept
the configured client certificates. This example does not enable the role's
managed-etcd mode; the role will not install or manage those etcd members.
Certificate issuance, distribution, renewal, firewall policy, and DCS
operations remain operator responsibilities. Do not replace the scoped
network rules with wildcard CIDRs or expose the Patroni API publicly.

## Playbook

```yaml
---
- name: "Install PostgreSQL Patroni members"
  hosts: postgres_patroni
  become: true
  roles:
    - role: ansible-iac-role-postgresql
      state: "install"
```
