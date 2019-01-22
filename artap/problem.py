from .datastore import SqliteDataStore, SqliteHandler
from .individual import Individual
from .utils import flatten
from .utils import ConfigDictionary
import collections
from abc import ABC, abstractmethod

import os
import tempfile
import multiprocessing
import logging

# surrogate
# from sklearn import linear_model
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern, ConstantKernel as C
# from sklearn.neural_network import MLPClassifier

"""
 Module is dedicated to describe optimization problem. 
"""

CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARN
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

_log_level = [CRITICAL, ERROR, WARNING, INFO, DEBUG]


class ProblemBase(ABC):

    def __init__(self):
        self.name: str = None
        self.description = ""
        self.populations: list = None
        self.parameters: dict = None
        self.costs: list = None
        self.data_store: SqliteDataStore = None

        # options
        self.options = ConfigDictionary()

        self.options.declare(name='calculate_gradients', default=False,
                             desc='calculate gradient for individuals')
        self.options.declare(name='save_level', default="problem",
                             desc='Save level')
        self.options.declare(name='log_level', default=logging.DEBUG, values=_log_level,
                             desc='Log level')
        self.options.declare(name='log_file_handler', default=False,
                             desc='Enable file handler')
        self.options.declare(name='log_db_handler', default=True,
                             desc='Enable DB handler')
        self.options.declare(name='log_console_handler', default=True,
                             desc='Enable console handler')
        # TODO: move to Algorithm class
        self.options.declare(name='max_processes', default=max(int(2 / 3 * multiprocessing.cpu_count()), 1),
                             desc='Max running processes')

    def get_parameters_list(self):
        parameters_list = []
        names = list(self.parameters.keys())
        i = 0
        for sub_dict in list(self.parameters.values()):
            parameter = [names[i]]
            parameter.extend(flatten(sub_dict.values()))
            parameters_list.append(parameter)
            i += 1
        return parameters_list


class Problem(ProblemBase):
    """ The Class Problem Is a main class which collects information about optimization task """

    MINIMIZE = -1
    MAXIMIZE = 1

    def __init__(self, name, parameters, costs, data_store=None, working_dir=None):

        super().__init__()
        self.name = name
        self.working_dir = working_dir

        forbidden_path = os.sep + "workspace" + os.sep + "common_data"
        if working_dir is not None:
            if forbidden_path in self.working_dir:
                raise IOError('Folder "/workspace/common_data" is read only.')

        self.parameters = parameters
        self.costs = {cost: 0.0 for cost in costs}

        # working dir
        """
        if working_dir is None:
            self.working_dir = tempfile.mkdtemp()
        else:
            # time_stamp = str(datetime.now()).replace(' ', '_').replace(':', '-')
            time_stamp = ""

            self.working_dir += time_stamp
            if not os.path.isdir(self.working_dir):
                os.mkdir(self.working_dir)
        """

        # create logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.options['log_level'])
        # create formatter
        formatter = logging.Formatter('%(asctime)s (%(levelname)s): %(name)s - %(funcName)s (%(lineno)d) - %(message)s')

        if self.options['log_console_handler']:
            # create console handler and set level to debug
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            # add formatter to StreamHandler
            stream_handler.setFormatter(formatter)
            # add StreamHandler to logger
            self.logger.addHandler(stream_handler)

        # working dir must be set
        if self.options['log_file_handler'] and working_dir:
            # create file handler and set level to debug
            file_handler = logging.FileHandler(self.working_dir + "/data.log")
            file_handler.setLevel(logging.DEBUG)
            # add formatter to FileHandler
            file_handler.setFormatter(formatter)
            # add FileHandler to logger
            self.logger.addHandler(file_handler)

        if data_store is None:
            self.data_store = SqliteDataStore(problem=self, working_dir=self.working_dir, create_database=True)
            self.data_store.create_structure_task(self)
            self.data_store.create_structure_individual(self.parameters, self.costs)
            self.data_store.create_structure_parameters(self.get_parameters_list())
            self.data_store.create_structure_costs(self.costs)

        else:
            self.data_store = data_store
        
        self.id = self.data_store.get_id()
        self.populations = []
        self.eval_counter = 0

        # working dir must be set
        if self.options['log_db_handler'] and isinstance(self.data_store, SqliteDataStore):
            # create file handler and set level to debug
            file_handler = SqliteHandler(self.data_store)
            file_handler.setLevel(logging.DEBUG)
            # add formatter to SqliteHandler
            file_handler.setFormatter(formatter)
            # add SqliteHandler to logger
            self.logger.addHandler(file_handler)

        self.logger.debug("START")
        # self.logger.debug('This message should go to the log file')
        # self.logger.info('So should this')
        # self.logger.warning('And this, too')

        # surrogate model
        self.surrogate = None

        self.surrogate_prepared = False
        self.surrogate_predict_counter = 0
        self.surrogate_counter_step = 30

        self.surrogate_x_data = []
        self.surrogate_y_data = []

    def __del__(self):
        pass

    def init_surrogate_model(self):
        # surrogate model
        kernel = C(1.0, (1e-3, 1e3)) * RBF(10, (1e-6, 3e2))
        kernel = 1.0 * Matern(length_scale=1.0, length_scale_bounds=(1e-5, 1e5), nu=1.5)
        self.surrogate = GaussianProcessRegressor(kernel=kernel)
        # self.surrogate = MLPClassifier(solver='lbfgs', alpha=1e-5, hidden_layer_sizes=(5, 2), random_state=1)

    def add_population(self, population):
        self.populations.append(population)

    def parameters_len(self):
        return len(self.parameters)

    # TODO: FIX table.append([parameter[2], parameter[3]])
    def get_bounds(self):
        table = []
        for parameter in self.get_parameters_list():
            table.append([parameter[2], parameter[3]])
        return table

    def evaluate_individual(self, x, population=0):
        """

        :param x:
        :param population:
        :return: cost which is calculated
        """

        individual = Individual(x, self, population)
        cost = individual.evaluate()
        self.populations[population].individuals.append(individual)

        return cost

    def evaluate_individual_scalar(self, x, population=0):
        """

        :param x:
        :param population:
        :return: cost which is calculated
        """

        cost = self.evaluate_individual(x, population)
        return cost[0]

    def evaluate_gradient_richardson(self, individual):
        n = len(self.parameters)
        gradient = [0] * n
        x0 = individual.parameters
        h = 1e-6
        y = self.evaluate_individual_scalar(x0)
        for i in range(len(self.parameters)):
            x = x0.copy()
            x[i] += h
            y_h = self.evaluate_individual_scalar(x)
            d_0_h = gradient[i] = (y_h - y) / h
            x[i] += h
            y_2h = self.evaluate_individual_scalar(x)
            d_0_2h = (y_2h - y) / 2 / h
            gradient[i] = (4*d_0_h - d_0_2h) / 3

        return gradient

    def evaluate_gradient(self, individual):
        n = len(self.parameters)
        gradient = [0]*n
        x0 = individual.parameters
        y = self.evaluate(x0)
        h = 1e-6
        for i in range(len(self.parameters)):
            x = x0.copy()
            x[i] += h
            y_h = self.evaluate(x)
            if isinstance(y_h, collections.Iterable):
                m = len(y_h)
                gradient[i] = []
                for j in range(m):
                    gradient[i].append((y_h[j] - y[j]) / h)
            else:
                gradient[i] = (y_h - y) / h

        return gradient

    def evaluate_surrogate(self, x: list):
        evaluate = True
        if self.surrogate_prepared:
            # predict
            p, sigma = self.surrogate.predict([x], return_std=True)
            # p = self.surrogate.predict([x])

            self.logger.debug("Surrogate: predict: x: {}, prediction: {}, sigma: {}".format(x, p[0], sigma))
            # sigma = 0
            # if p[0][0] > 0 and p[0][1] > 0 and sigma < 0.01:
            if sigma < 3:
                # set predicted value
                value = p[0].tolist()
                self.surrogate_predict_counter += 1
                evaluate = False

        if evaluate:
            value = self.evaluate(x)

            # store surrogate
            self.surrogate_x_data.append(x)
            self.surrogate_y_data.append(value)

            # increase counter
            self.eval_counter += 1

            if self.eval_counter % self.surrogate_counter_step == 0:
                # surrogate model
                counter_eff = 100.0 * self.surrogate_predict_counter / (self.eval_counter + self.surrogate_predict_counter)
                # speed up
                if counter_eff > 30:
                    self.surrogate_counter_step = int(self.surrogate_counter_step * 1.3)
                self.logger.debug("Surrogate: learning: {}, predict eff: {}, counter_step: {}"
                                  .format(self.surrogate_predict_counter, counter_eff, self.surrogate_counter_step))

                # clf = linear_model.SGDRegressor()
                # clf = linear_model.SGDRegrBayesianRidgeessor()
                # clf = linear_model.LassoLars()
                # clf = linear_model.TheilSenRegressor()
                # clf = linear_model.LinearRegression()

                # fit model
                self.surrogate.fit(self.surrogate_x_data, self.surrogate_y_data)
                self.surrogate_prepared = True

        return value

    def get_initial_values(self):
        values = []
        for parameter in self.parameters.items():
            if 'initial_value' in parameter[1]:
                values.append(parameter[1]['initial_value'])
            else:
                values.append(0)
        return values

    def eval_batch(self, table):
        n = len(table)
        results = [0] * n
        for i in range(n):
            results[i] = self.evaluate(table[i])
        return results

    @abstractmethod
    def evaluate(self, x: list):
        """ :param x: list of the variables """
        pass

    def evaluate_constraints(self, x: list):
        """ :param x: list of the variables """
        pass


class ProblemDataStore(ProblemBase):

    def __init__(self, data_store, working_dir=None):

        super().__init__()
        self.data_store = data_store
        self.data_store.read_problem(self)

        if working_dir is None:
            self.working_dir = tempfile.mkdtemp()
        else:
            self.working_dir = working_dir + self.name

    def to_table(self):
        table = []
        line = ["Population ID"]
        for parameter in self.get_parameters_list():
            line.append(parameter[0])
        for cost in self.costs:
            line.append(cost)
        table.append(line)
        for population in self.populations:
            for individual in population.individuals:
                line = [individual.population_id]
                for parameter in individual.parameters:
                    line.append(parameter)
                for cost in individual.costs:
                    line.append(cost)
                table.append(line)
        return table
