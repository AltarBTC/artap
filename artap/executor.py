import time
import re
import paramiko
import sys
import tempfile
import traceback
import os
from string import Template

from artap.enviroment import Enviroment


class Executor:
    """
    Function is a class representing objective or cost function for 
    optimization problems.
    """

    def __init__(self, inputs=1, outputs=1):
        self.number_inputs = inputs
        self.number_outputs = outputs

    def exec(self, x):
        pass

class ComsolExecutor(Executor):

    def __init__(self, inputs, outputs, parameters, model_name, output_filename):
        super().__init__(inputs, outputs)
        self.parameters = parameters
        self.output_filename = output_filename
        self.model_name = model_name

    def run_comsol(self, x):
        """ Funtion compile model_name.java file and run Comsol in a batch mode."""
        import os
        comsol_path = Enviroment.comsol_path
        run_string = comsol_path + "comsol batch -inputfile " + self.model_name + " -nosave -pname "

        # add parameters
        for parameter in self.parameters:
            run_string += parameter + ","
        # remove last comma
        if (len(self.parameters)) > 1:
            run_string = run_string[:-1]

        run_string += " -plist "

        # add values
        for val in x:
            run_string += str(val) + ","
        # remove last comma
        if (len(x)) > 1:
            run_string = run_string[:-1]

        # print(run_string)
        os.system(run_string)

    def eval(self, x):
        # Parse the output file from the external code and set the value of y
        self.run_comsol(x)

        y = 0
        with open(self.output_filename) as file:
            data = file.read()
            lines = data.split("\n")
            y = float(lines[5])
        return y

class RemoteExecutor(Executor):
    """
        Allowes distributing of calculation of obejctive functions. 
        """

    def __init__(self, hostname=None,
                 username=None, password=None, port=22, working_dir=None, suplementary_files=[]):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.working_dir = working_dir
        self.suplementary_files = suplementary_files

        self.script = ""

        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname=self.hostname, username=self.username, password=self.password)

            self.status = "None"
            self.host = ""

            self.remote_dir = self.create_remote_dir()

        except Exception as e:
            print('*** Caught exception: %s: %s' % (e.__class__, e))
            traceback.print_exc()
            try:
                self.client.close()
            except:
                pass
            sys.exit(1)

    def __del__(self):
        # close connection
        self.client.close()

    def create_remote_dir(self, dir = "htcondor"):
        try:
            self.client.exec_command("mkdir " + dir)
            self.client.exec_command("mkdir " + dir + "/" + "artap")

            return dir + "/" + "artap"

        except Exception as e:
            print('*** Caught exception: %s: %s' % (e.__class__, e))
            traceback.print_exc()
            try:
                self.client.close()
            except:
                pass
            sys.exit(1)

    def transfer_files_to_remote(self, source_file, destination_file):
        source = source_file
        dest = self.remote_dir + "/" + destination_file

        try:
            sftp = paramiko.SFTPClient.from_transport(self.client.get_transport())
            sftp.put(source, dest)

        except Exception as e:
            print('*** Caught exception: %s: %s' % (e.__class__, e))
            traceback.print_exc()
            try:
                self.client.close()
            except:
                pass
            sys.exit(1)

    def transfer_files_from_remote(self, source_file, destination_file):
        dest = destination_file
        source = self.remote_dir + "/" + source_file

        try:
            sftp = paramiko.SFTPClient.from_transport(self.client.get_transport())
            sftp.get(source, dest)

        except Exception as e:
            print('*** Caught exception: %s: %s' % (e.__class__, e))
            traceback.print_exc()
            try:
                self.client.close()
            except:
                pass
            sys.exit(1)

    def run_command_on_remote(self, command):
        # Run ssh command
        output = ""
        try:
            if (self.remote_dir == ""):
                stdin, stdout, stderr = self.client.exec_command(command)
            else:
                stdin, stdout, stderr = self.client.exec_command("cd " + self.remote_dir + "; " + command)

            for line in stdout:
                print(line.strip('\n'))
                output += line.strip('\n')
            for line in stderr:
                print(line.strip('\n'))

        except Exception as e:
            print('*** Caught exception: %s: %s' % (e.__class__, e))
            traceback.print_exc()
            try:
                self.client.close()
            except:
                pass
            sys.exit(1)

        return output

    def eval(self, x):

        for file in self.suplementary_files:
            self.transfer_files_to_remote(self.working_dir + '/' + file, './' + file)

        parameters_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        parameters_file.write(str(x[0]) + " " + str(x[1]))
        parameters_file.close()

        output_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        output_file.close()

        self.transfer_files_to_remote(parameters_file.name, 'parameters.txt')
        self.run_command_on_remote("python3 remote.py")

        self.transfer_files_from_remote('output.txt', output_file.name)
        with open(output_file.name) as file:
            y = float(file.read())

        os.remove(parameters_file.name)
        os.remove(output_file.name)

        return y


class CondorComsolJobExecutor(RemoteExecutor):
    """ Allwes submit goal function calculation as a HT Condor job """

    def __init__(self, parameters, model_name, output_filename, hostname=None,
                 username=None, password=None, port=22, working_dir=None, suplementary_files=None):

        self.parameters = parameters
        self.output_filename = output_filename
        self.model_name = model_name

        suplementary_files = []
        suplementary_files.append(self.model_name)

        super().__init__(hostname, username, password, port, working_dir=working_dir,
                         suplementary_files=suplementary_files)

    def eval_batch(self, table):
        # add parameters
        param_names_string = ""
        for parameter in self.parameters:
            param_names_string += parameter + ","
        # remove last comma
        if (len(self.parameters)) > 1:
            param_names_string = param_names_string[:-1]

        ids = []
        i = 0
        for x in table:
            # add values
            param_values_string = ""
            for val in x:
                param_values_string += str(val) + ","
            # remove last comma
            if (len(x)) > 1:
                param_values_string = param_values_string[:-1]

            i += 1
            with open(self.working_dir + "/remote.tp", 'r') as job_file:
                job_file = Template(job_file.read())

            output_filename = os.path.basename(self.output_filename)
            job_file = job_file.substitute(model_name=os.path.basename(self.model_name), output_file=os.path.splitext(output_filename)[0] + str(i) + os.path.splitext(output_filename)[1],
                                           log_file="comsol%d.log" %i, run_file="run%d.sh" %i,
                                           param_names=param_names_string, param_values=param_values_string)
            with open(self.working_dir + "/remote%d.job" %i, 'w') as job_remote_file:
                job_remote_file.write(job_file)
            self.suplementary_files.append("remote%d.job" % i)

            with open(self.working_dir + "/run.tp", 'r') as run_file:
                run_file = Template(run_file.read())

            run_file = run_file.substitute(output_base_file=output_filename, output_file=os.path.splitext(output_filename)[0] + str(i) + os.path.splitext(output_filename)[1])
            with open(self.working_dir + "/run%d.sh" %i, 'w') as job_run_file:
                job_run_file.write(run_file)
            self.suplementary_files.append("run%d.sh" %i)

            comsol_path = Enviroment.comsol_path

            for file in self.suplementary_files:
                self.transfer_files_to_remote(self.working_dir + '/' + file, './' + file)
            output = self.run_command_on_remote("condor_submit remote%d.job" %i)
            id = re.search('cluster \d+', output).group().split(" ")[1]
            ids.append(id)
            start = time.time()

        while (output != ""):  # If the job is complete it disappears from que
            output=""
            for id in ids:
                output += self.run_command_on_remote("condor_q -l " + str(id))
            print(time.time() - start)
            if (time.time() - start) > 140:  # Time out is 20 seconds
                break

        result = []
        for j in range(len(table)):
            index = j + 1
            self.transfer_files_from_remote('./max%d.txt' %index, self.working_dir + '/max%d.txt' %index )
            with open(self.working_dir + "/max%d.txt" %index) as file:
                lines = file.readlines()
                y = float(lines[5])
                result.append(y)

        return result


    def eval(self, x):

        # with open(self.working_dir + "/parameters.txt", 'w') as input_file:
            # input_file.write(str(x[0]) + " " + str(x[1]))

        # self.suplementary_files.append("parameters.txt")

        with open(self.working_dir + "/remote.tp", 'r') as job_file:
            job_file = Template(job_file.read())

        job_file = job_file.substitute(input_file='elstat.java')

        with open(self.working_dir + "/remote.job", 'w') as job_output_file:
            job_output_file.write(job_file)

        with open(self.working_dir + "/elstat.tp", 'r') as input_file:
            begin_params = "//---------------------\n"
            java_str = input_file.read()
        index = java_str.find(begin_params) + len(begin_params)
        output_java = java_str[:index]
        output_java += 'model.param().set("a", %f);\n' % x[0]
        output_java += 'model.param().set("b", %f);\n' % x[1]
        output_java += java_str[index:]

        with open(self.working_dir + "/elstat.java", 'w') as output_file:
            output_file.write(output_java)

        comsol_path = Enviroment.comsol_path
        #compile_string = comsol_path + "comsol compile " + self.working_dir + "/elstat.java"

        #os.system(compile_string)  # it is necessary only when .java file is changed

        for file in self.suplementary_files:
            self.transfer_files_to_remote(self.working_dir + '/' + file, './' + file)
        output = self.run_command_on_remote("condor_submit ./remote.job")
        print("output:", output)
        id = re.search('cluster \d+', output).group().split(" ")[1]
        output = "run"
        start = time.time()
        while (output != ""):  # If the job is complete it disappears from que
            output = self.run_command_on_remote("condor_q -l " + str(id))
            print(time.time() - start)
            if (time.time() - start) > 140:  # Time out is 20 seconds
                break

        self.transfer_files_from_remote('./max.txt', self.working_dir + '/max.txt')
        with open(self.working_dir + "/max.txt") as file:
            y = file.readlines()
        i = 0;
        for line in y:
            if line == '=======================================================\n':
                i = i +1
                break
            i = i + 1
        result = float(y[i])
        return result


class CondorPythonJobExecutor(RemoteExecutor):
    """ Allwes submit goal function calculation as a HT Condor job """

    def __init__(self, parameters, model_name, output_filename, hostname=None,
                 username=None, password=None, port=22, working_dir=None, suplementary_files=None):

        self.parameters = parameters
        self.output_filename = output_filename
        self.model_name = model_name


        super().__init__(hostname, username, password, port, working_dir=working_dir,
                         suplementary_files=suplementary_files)

    def eval(self, x):

        parameters_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        parameters_file.write(str(x[0]) + " " + str(x[1]))
        parameters_file.close()

        output_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        output_file.close()

        self.transfer_files_to_remote(parameters_file.name, 'parameters.txt')

        for file in self.suplementary_files:
            self.transfer_files_to_remote(self.working_dir + '/' + file, './' + file)
        output = self.run_command_on_remote("condor_submit ./remote.job")
        print("output:", output)
        id = re.search('cluster \d+', output).group().split(" ")[1]
        output = "run"
        start = time.time()
        while (output != ""):  # If the job is complete it disappears from que
            output = self.run_command_on_remote("condor_q -l " + str(id))
            print(time.time() - start)
            if (time.time() - start) > 140:  # Time out is 20 seconds
                break

        self.transfer_files_from_remote('./' + self.output_filename, self.working_dir + self.output_filename)
        with open(self.working_dir +  self.output_filename) as file:
            lines = file.readlines()
            y = float(lines[0])

        return y
