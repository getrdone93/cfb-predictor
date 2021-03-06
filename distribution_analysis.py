import matplotlib.pyplot as plt
import estimator as est
import team_game_statistics as tgs
from scipy.stats import shapiro
import numpy as np

#There seems to be a correlation between the statistic value of the Shapiro-Wilk test and the 
#"normality" of the given distribution. We will say that any distribution with a statistic 
#greater than or equal to .8 is a failure to reject H0. Also, the p values are incredibly 
#low for all tests, but I am unsure why at this point.
SW_NORM_THRESHOLD = 0.80

def reorder(features):
    """Orders features such that -0 feature follows -1 feature

    Args:
         features: map of features to values
    
    Returns: tuple with two entries, where the first is the ordered features
             and the second is any features where a matching feature could 
             not be found
    """

    res = []
    no_match = []
    for field in [x for x in set(features.keys()) if '-0' in x]:
        lis = [e for e in [x for x in set(features.keys()) if '-1' in x] if e[0 : len(e) - 2] == field[0 : len(field) - 2]]
        if len(lis) == 1:
            res.append((field, features[field]))
            res.append((lis[0], features[lis[0]]))
        else:
            no_match.append(field)

    return res, no_match

def histogram(avgs, team_stats):
    """Draws a histogram plot for each field in avgs

    Args: 
         avgs: Averages for each team in each game
         team_stats: stats for each team

    Returns: None
    """

    fields, _ = est.input_data(game_averages=avgs, labels=tgs.add_labels(team_game_stats=team_stats))

    data, _ = reorder(features=fields)

    for i in range(1, len(data), 2):
        plt.figure(num=i)
        plt.hist(data[i - 1][1], bins='auto')
        plt.title(data[i - 1][0])

        plt.hist(data[i][1], bins='auto')
        plt.title(data[i][0])

    plt.show()

def shapiro_wilk(distributions):
    """Computes the shapiro wilk statistical test for a given map of distributions

    Args:
         distributions: map of field name to values where values, in most calling 
         contexts, are the averages
   
    Returns: map of field name to shapiro wilk score
    """

    result = {}
    for k, d in distributions.items():
        result[k] = shapiro(d)
    
    return result

def similar_field(field, all_fields):
    """Given a field and a collection of fields, finds the corresponding
       field by checking equality of the first n - 2 characters

    Args:
         field: field to search for
         all_fields: collection of fields to search within
    
    Returns: the first matching field if one is found, otherwise None
    """

    res = [e for e in all_fields if e[0 : len(e) - 2] == field[0 : len(field) - 2]]
    return res[0] if res else None

def normality_filter(shapiro_wilk, threshold):
    """Given shapiro wilk scores and a threshold, filters distributions
       according to their shaprio wilk statistical value being greater 
       than or equal to the given threshold. Note this function will 
       opt a field in if its corresponding field passes the threshold.

    Args:
         shaprio_wilk: map of fields to their shapiro_wilk scores
         threshold: value for comparing shapiro wilk statistical 
                    scores

    Returns: map of fields to their shapiro wilk scores
    """

    result = {}
    for f, val in [i for i in set(shapiro_wilk.items()) if '-0' in i[0]]:
        sf = similar_field(field=f, all_fields=[k for k in set(shapiro_wilk.keys()) if '-1' in k])
        if sf and (shapiro_wilk[sf][0] >= threshold or val[0] >= threshold):
            result[f] = val
            result[sf] = shapiro_wilk[sf]
    return result

def normal_dists(field_avgs):
    """Computes shapiro wilk scores for a given set of averages 
       or distributions and returns a filtered set of those distributions
       by their shapiro wilk scores

    Args: 
         field_avgs: map of field name to its average values
    
    Returns: map of fields to their shapiro wilk scores
    """

    sw = shapiro_wilk(distributions=field_avgs)
    norms = normality_filter(shapiro_wilk=sw, threshold=SW_NORM_THRESHOLD)
    
    return norms

def z_scores_args(data, mean, stddev):
    """Computes zscores for given data, based off of a given mean and
       stddev

    Args:
         data: input values
         mean: mean of input values
         stddev: stddev of input values

    Returns: zscores of data
    """

    return [(d - mean) / stddev for d in data]

def z_scores(data):
    """Computes zscores for given data, based off of a mean and stddev
       derived from data 

    Args:
         data: input values

    Returns: zscores of data
    """

    return z_scores_args(**{'data': data, 'mean': np.average(data), 'stddev': np.std(data)})

def reverse_zscores(data, mean, stddev):
    """Reverses zscores for given data, based off of a given mean and
       stddev

    Args:
         data: input values
         mean: mean of input values
         stddev: stddev of input values

    Returns: original values of data
    """
    
    return [v * stddev + mean for v in data]
