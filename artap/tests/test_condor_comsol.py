from unittest import TestCase, main
import getpass

from artap.executor import CondorComsolJobExecutor
from artap.problem import Problem
from artap.enviroment import Enviroment
from artap.population import Population_NSGA_II


class TestProblem(Problem):
    """ Describe simple one objective optimization problem. """

    def __init__(self, name):

        parameters = {'a': {'initial_value': 10, 'bounds': [1, 5], 'precision': 1e-1},
                      'b': {'initial_value': 10, 'bounds': [10, 15], 'precision': 1e-1}}
        costs = ['F1']
        working_dir = "./workspace/condor_comsol/"
        super().__init__(name, parameters, costs, working_dir=working_dir, save_data=True)
        self.max_population_number = 1
        self.max_population_size = 5

        output_file = "max.txt"
        model_file = "elstat.mph"

        # current username
        if Enviroment.condor_host_login == "":
            user = getpass.getuser()
        else:
            user = Enviroment.condor_host_login
        # host        

        host = Enviroment.condor_host_ip

        self.executor = CondorComsolJobExecutor(parameters, model_file, output_file,
                                                username=user, hostname=host, working_dir=working_dir)

    def eval(self, x):
        result = self.executor.eval(x)
        return result


class TestCondor(TestCase):
    """ Tests simple optimization problem where calculation of 
        goal function is submitted as a job on HtCondor. 
    """

    def test_condor_run(self):
        """ Tests one calculation of goal function."""
        problem = TestProblem("Condor Comsol Problem")
        population = Population_NSGA_II(problem)
        population.gen_random_population(15, len(problem.parameters),
                                         problem.parameters)
        population.evaluate()


if __name__ == '__main__':
    main()