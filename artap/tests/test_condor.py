from unittest import TestCase, main
import getpass

from artap.executor import CondorPythonJobExecutor
from artap.problem import Problem
from artap.enviroment import Enviroment


class TestProblem(Problem):
    """ Describe simple one objective optimization problem. """

    def __init__(self, name):

        parameters = {'x_1': {'initial_value': 5},
                      'x_2': {'initial_value': 10}}
        costs = ['F1']
        working_dir = "./workspace/condor/"

        super().__init__(name, parameters, costs, working_dir=working_dir, save_data=False)

        self.max_population_number = 1
        self.max_population_size = 1
        self.save_data = False

        supplementary_files = ["remote.job", "remote.py"]

        output_file = "output.txt"
        model_file = "remote.py"

        # current username
        if Enviroment.condor_host_login == "":
            user = getpass.getuser()
        else:
            user = Enviroment.condor_host_login
        # host        

        host = Enviroment.condor_host_ip

        self.executor = CondorPythonJobExecutor(self.parameters, model_file, output_file,
                                                username=user, hostname=host, working_dir=working_dir,
                                                supplementary_files=supplementary_files)

    def eval(self, x):
        result = self.executor.eval(x)
        return result


class TestCondor(TestCase):
    """ Tests simple optimization problem where calculation of 
        goal function is submitted as a job on HtCondor. 
    """

    def test_condor_run(self):
        """ Tests one calculation of goal function."""
        problem = TestProblem("Condor Problem")
        result = problem.eval([1, 1])
        self.assertAlmostEqual(result, 2)


if __name__ == '__main__':
    main()
