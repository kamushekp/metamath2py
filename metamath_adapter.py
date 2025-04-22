import os
import subprocess
from queue import Queue, Empty


def read_until_input_invite(process):
    prompt = ''
    while not prompt.endswith('MM>'):
        char = process.stdout.read(1)  # Читаем по одному символу
        if char == '':  # Если ничего не возвращается, значит EOF
            break
        prompt += char
        if prompt.endswith('\nMM>'):  # Ищем приглашение с новой строки
            prompt = prompt[:-4]
            break
    return prompt


def launch_in_queue_reader(stream, queue):
    while True:
        line = stream.readline()
        queue.put(line)
        if not line:
            break


def launch_metamath_base():
    work_dir = r'C:\Users\kamus\PycharmProjects\metamath'
    metamath = os.path.join(work_dir, 'metamath.exe')
    process = subprocess.Popen([metamath], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=work_dir)
    read_until_input_invite(process)

    process.stdin.write('read set_normal.mm\n')
    process.stdin.flush()
    read_until_input_invite(process)

    process.stdin.write('SET SCROLL CONTINUOUS\n')
    process.stdin.flush()
    read_until_input_invite(process)

    process.stdin.write('SET WIDTH 100000\n')
    process.stdin.flush()
    read_until_input_invite(process)
    return process


def read_from_flow_queue(queue: Queue):
    while True:
        try:
            line = queue.get(timeout=2)
        except Empty:
            return
        yield line


class MetamathHandler:
    def __init__(self):
        self.process = launch_metamath_base()

    def read_proof(self, statement_name: str):
        try:
            self.process.stdin.write(f'show proof {statement_name} /lemmon/renumber/all\n')
            self.process.stdin.flush()
            return read_until_input_invite(self.process)
        except Exception as e:
            print(e)
            return ''