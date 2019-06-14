import os
import json
import random
import shutil
import time

import subprocess

wallet_dir = "wallet/"
ckb_node_name = "ckb-node"
ckb_node_volume = "ckb-testnet"

def execCmd(cmd):
  r = os.popen(cmd)
  text = r.read()
  r.close()
  return text


def exec_cmd_nonblock(cmd):
    subprocess.Popen(cmd, shell = True)


def appendFile(filename, data):
  f = open(filename, "a")
  f.write(data)
  f.close()


def random_create_wallet():
    private_name = random.randrange(0, pow(2, 128))
    print(private_name)
    cmd = "ckb-cli wallet generate-key --privkey-path " + wallet_dir + str(private_name)
    output = execCmd(cmd)
    lines = output.splitlines(True)
    block_assembler = lines[2] + lines[3] + lines[4]
    address_json = lines[6]
    address = json.loads(address_json)["address"]
    os.rename(wallet_dir+str(private_name), wallet_dir+address)

    return block_assembler, address


def modify_config(block_assembler, address):
    shutil.copyfile("ckb.toml.example","ckb.toml")
    shutil.copyfile("ckb-miner.toml.example", "ckb-miner.toml")
    appendFile("ckb.toml", block_assembler)


# untest
def copy_config_to_container():
    tar_cmd = "tar --owner=1000 --group=1000 -cf - ckb.toml ckb-miner.toml | " \
              "docker cp - ckb-node:/var/lib/ckb/"
    execCmd(tar_cmd)


def init_ckb_node():
    result = execCmd("docker ps -a")
    if ckb_node_name not in result:
        print("init ckb node ******")
        execCmd("docker volume create %s" % ckb_node_volume)
        execCmd(
            "docker run --rm -it -v %s:/var/lib/ckb nervos/ckb:latest init --chain testnet --force" % ckb_node_volume)
        execCmd(
            "docker create -it --network host -v %s:/var/lib/ckb --name %s nervos/ckb:latest run" %
            (ckb_node_volume, ckb_node_name))
        execCmd("docker cp %s:/var/lib/ckb/ckb.toml ckb.toml.example" % ckb_node_name)
        execCmd("docker cp %s:/var/lib/ckb/ckb-miner.toml ckb-miner.toml.example" % ckb_node_name)
        return
    print("already init *****")

def start_ckb_node():
    result = execCmd("docker ps")
    if ckb_node_name in result:
        print("stoping ckb node")
        execCmd("docker stop %s" % ckb_node_name)
    block_assembler, address = random_create_wallet()
    modify_config(block_assembler, address)
    copy_config_to_container()
    execCmd("docker start %s" % ckb_node_name)
    return address

def stop_ckb_node():
    execCmd("docker stop %s" % ckb_node_name)


def start_mining(number_of_thread):
    for i in range(number_of_thread):
        print("start miner ", i + 1)
        exec_cmd_nonblock("nohup docker exec %s ckb miner </dev/null &>/dev/null &" % ckb_node_name)


def clean_node():
    print("clear node and volume")
    execCmd("docker stop %s" % ckb_node_name)
    execCmd("docker rm %s" % ckb_node_name)
    execCmd("docker volume rm %s" % ckb_node_volume)

def mining_success(address):
    while(True):
        try:
            cmd_result = execCmd("ckb-cli wallet get-balance --address %s " % address)
            print(cmd_result)
            json_load = json.loads(cmd_result)
            utxo_count = json_load["Capacity"]["utxo_count"]
            print(utxo_count)

            if utxo_count == None:
                print("************continue mining **********")
                time.sleep(3)
            else:
                break 
        except:
            time.sleep(3)
            print("waiting node startup")


def run():
    init_ckb_node()
    while(True):
        address = start_ckb_node()
        time.sleep(5)

        start_mining(3)
        mining_success(address)

        stop_ckb_node()
        time.sleep(10)

run()





