import main as temp_lib
import sys
import model
import team_game_statistics as tgs
import numpy as np
import copy
from dateutil import parser as du
import math
import random
from random import randint
import tensorflow as tf
import glob
import os.path as path
import pickle
import time
import distribution_analysis as da
from proto import estimator_pb2
from google.protobuf import text_format
import argparse
from google.protobuf.json_format import MessageToDict
from functools import partial
from os import listdir
import re

TF_FEATURE_NAME = lambda f: f.replace(' ', '-')
BATCH_SIZE = 20
TRAIN_STEPS = 3000
RANDOMIZER = {'stochastically_randomize_vector': stochastically_randomize_vector, 
                       'stochastically_randomize_half_vector': stochastically_randomize_half_vector}
ACTIVATION = {'relu': tf.nn.relu, 'relu6': tf.nn.relu6, 'sigmoid': tf.math.sigmoid, 'leaky_relu': tf.nn.leaky_relu}
REGULARIZATION = {'l2': tf.contrib.layers.l2_regularizer, 'l1': tf.contrib.layers.l1_regularizer}

def loop_through(**kwargs):
    data = kwargs['data']

    for k, v in data.iteritems():
        print("k " + str(k))
        #print("v " + str(v))
        # for tid, stat in v.iteritems():
        #     print("tid " + str(tid))
        #     print("stat len " + str(len(stat)))
        print("len(v) " + str(len(v)))
        #print("keys of v " + str(v.keys()))
        #raw_input()

def averages(**kwargs):
    team_game_stats, game_infos, skip_fields = kwargs['team_game_stats'], kwargs['game_infos'],\
                                               kwargs['skip_fields']

    game_avgs = {}
    for gid in team_game_stats.keys():
        avgs = model.team_avgs(game_code_id=gid, game_data=game_infos, tg_stats=team_game_stats)
        if len(avgs) == 2:
            game_avgs[gid] = {}
            for tid, stats in avgs.iteritems():
                game_avgs[gid][tid] = {k: stats[k] for k in set(stats.keys()).difference(skip_fields)}
        else:
            pass
        
    return game_avgs

def input_data(**kwargs):
    game_avgs, input_labels = kwargs['game_averages'], kwargs['labels']

    features = {}
    labels = []
    for gid, team_avgs in game_avgs.iteritems():
        for ta, feature_team_id, fid in zip(team_avgs.iteritems(), ['-0', '-1'], [0, 1]):
            tid, stats = ta
            for name, value in stats.iteritems():
                stat_key = TF_FEATURE_NAME(name + feature_team_id)
                if stat_key not in features:
                    features[stat_key] = []
                features[stat_key].append(value)
            if input_labels[gid]['Winner']['Team Code'] == tid:
                labels.append(fid)

    for k in features.keys():
        features[k] = np.array(features[k])

    return features, np.array(labels)

def histogram_games(**kwargs):
    game_infos, game_stats, histo_key = kwargs['game_infos'], kwargs['game_stats'], kwargs['histo_key']

    histo = {}
    for gid in game_stats.keys():
        info = game_infos[gid]
        if info[histo_key] not in histo:
            histo[info[histo_key]] = []
        histo[info[histo_key]].append(gid)
    
    return histo

def sort_by(**kwargs):
    input_map, key_sort = kwargs['input_map'], kwargs['key_sort']

    lis = list(input_map.iteritems())
    lis.sort(key=key_sort)

    return lis

def stochastic_split_data(**kwargs):
    gh, sp, shc = kwargs['game_histo'], float(kwargs['split_percentage']), kwargs['histo_count']

    train = []
    test = []
    train_divi = True
    for k, count in shc.iteritems():
        if count == 1:
            if train_divi:
                train.append(gh[k][0])
                train_divi = False
            else:
                test.append(gh[k][0])
                train_divi = True
        elif count == 2:
            num = randint(0, 1)
            train.append(gh[k][num])
            test.append(gh[k][int(not num)])
        else:
            train_split = int(round(count * sp))
            test_split = count - train_split
            if test_split == 0:
                train_split = int(math.ceil(float(count) / 2))
            ind_range = set(range(len(gh[k])))
            train_ind = set(random.sample(ind_range, train_split))
            test_ind = ind_range.difference(train_ind)
            train += [gh[k][e] for e in train_ind]
            test += [gh[k][e] for e in test_ind]

    return train, test

def static_split_data(**kwargs):
    gh, sp, shc = kwargs['game_histo'], float(kwargs['split_percentage']), kwargs['histo_count']

    train = []
    test = []
    train_divi = True
    keys = list(gh.keys())
    keys.sort(key=lambda x: du.parse(x))
    for d in keys:
        count = shc[d]
        k = d
        if count == 1:
            if train_divi:
                train.append(gh[k][0])
                train_divi = False
            else:
                test.append(gh[k][0])
                train_divi = True
        elif count == 2:
            train.append(gh[k][0])
            test.append(gh[k][1])
        else:
            train_split = int(round(count * sp))
            test_split = count - train_split
            if test_split == 0:
                train_split = int(math.ceil(float(count) / 2))
            num_games = len(gh[k])
            ind_range = set(range(num_games))
            train_ind = set(range(int(math.floor(num_games * sp))))
            test_ind = ind_range.difference(train_ind)
            train += [gh[k][e] for e in train_ind]
            test += [gh[k][e] for e in test_ind] 

    train.sort()
    test.sort()
    return train, test

def split_by_date(**kwargs):
    split, gs = kwargs['split'], kwargs['game_info']

    tdh = {}
    for gid in split:
        if gs[gid]['Date'] not in tdh:
            tdh[gs[gid]['Date']] = []
        tdh[gs[gid]['Date']].append(gid)

    tdh = {k: len(tdh[k]) for k in tdh.keys()}
    return sort_by(input_map=tdh, key_sort=lambda x: du.parse(x[0]))

def visualize_split(**kwargs):
    split, gs, tg = kwargs['split'], kwargs['game_info'], kwargs['total_games']

    train = split_by_date(split=split[0], game_info=gs)
    test = split_by_date(split=split[1], game_info=gs)  

    for tr, tst in zip(train, test):
        print("train: %s\ttest: %s" % (str(tr), str(tst)))

    print("Defensive test. Intersection of train and test should be empty, (intersection train test): " 
          + str(set(split[0]).intersection(set(split[1]))))
    print("Addition of splits should equal total games. Total games: %s Addition: %s" 
          % (str(tg), str(len(split[0]) + len(split[1]))))

def stochastically_randomize_vector(**kwargs):
    in_net, r = kwargs['net'], kwargs['rate']
    net = tf.map_fn(lambda gf: tf.cond(tf.equal(tf.constant(0), tf.random.uniform([1], 
                                       maxval=int(r), dtype=tf.int32))[0], 
                                       true_fn=lambda: tf.random_shuffle(gf), 
                                       false_fn=lambda: gf), in_net)
    return net

def stochastically_randomize_half_vector(**kwargs):
    in_net, r, ub = kwargs['net'], kwargs['rate'], 64
    keep_range = tf.cond(tf.equal(tf.constant(0), tf.random.uniform([1], maxval=2, dtype=tf.int32))[0], 
                         true_fn=lambda: tf.range(0, ub / 2), 
                         false_fn=lambda: tf.range(ub / 2, ub))
    randomize_range = tf.sets.difference([tf.range(ub)], [keep_range]).values
    net = tf.map_fn(lambda gf: tf.cond(tf.equal(tf.constant(0), tf.random.uniform([1], maxval=r, dtype=tf.int32))[0], 
                                           true_fn=lambda: tf.gather(gf, tf.concat([keep_range, 
                                           tf.random_shuffle(randomize_range)], axis=0)), 
                                           false_fn=lambda: gf), in_net)
    return net

def randomize_vector(**kwargs):
    in_net = kwargs['net']
    return tf.map_fn(lambda gf: tf.random_shuffle(gf), in_net)

def model_fn(features, labels, mode, params):
    ec, fc, da, rf, r, do, hu, n, reg, act, ty, ol, lr, t = params['estimator_config'], params['feature_columns'],\
                                                            'dataAugment', 'randomizerFunc', 'rate', 'dropout',\
                                                            'hiddenUnit', 'neurons', 'regularization', 'activation',\
                                                            'type', 'outputLayer', 'learningRate', 'train'
    hidden_units = ec.get(hu)
    net = tf.feature_column.input_layer(features, params['feature_columns'])

    if mode == tf.estimator.ModeKeys.TRAIN:
        ub = len(features)

        if ec.get(da):
            net = RANDOMIZER.get(ec.get(da).get(rf))(net=net, rate=ec.get(da).get(r))        
            net = tf.reshape(net, [-1, ub])

    tf.summary.histogram('input_layer', net)
    if ec.get(do):
        net = tf.nn.dropout(net, keep_prob=ec.get(do).get(r))

    #hidden layer
    for unit, num in zip(hidden_units, range(len(hidden_units))):
        layer_params = {}
        layer_params.update({'units': unit.get(n)})
        if unit.get(reg):
            layer_params.update({'kernel_regularizer': partial(REGULARIZATION.get(unit.get(reg).get(ty)), 
                                                              unit.get(reg).get(r))})
        net = tf.layers.dense(net, **layer_params)
        tf.summary.histogram("weights_%s_%s" % (str(unit.get(n)), str(num)), net)

        if unit.get(act):
            net = ACTIVATION.get(unit.get(act).get(ty))(net, name=unit.get(act).get(ty) + str(unit.get(n)))
            tf.summary.histogram("activations_%s_%s" % (str(unit.get(n)), str(num)), net)

    #logits
    output_params = {}
    output_params.update({'units': ec.get(ol).get(n)})
    if ec.get(ol).get(reg):
        output_params.update({'kernel_regularizer': partial(REGULARIZATION.get(ec.get(ol).get(reg).get(ty)), 
                                                           ec.get(ol).get(reg).get(r))})
    if ec.get(ol).get(act):
        output_params.update({'activation': partial(ACTIVATION.get(ec.get(ol).get(act).get(ty)), 
                           name=ec.get(ol).get(act).get(ty) + str(unit.get(n)))})
    net = tf.layers.dense(net, **output_params)

    tf.summary.histogram('logits_' + str(2), net)

    predicted_classes = tf.argmax(net, 1)
    if mode == tf.estimator.ModeKeys.PREDICT:
        predictions = {
            'class_ids': predicted_classes[:, tf.newaxis],
            'probabilities': tf.nn.softmax(net),
            'logits': net,
        }
        return tf.estimator.EstimatorSpec(mode, predictions=predictions)
    
    loss = tf.losses.sparse_softmax_cross_entropy(labels=labels, logits=net)
    accuracy = tf.metrics.accuracy(labels=labels,
                                   predictions=predicted_classes,
                                   name='acc_op')

    tf.summary.scalar('accuracy', accuracy[1])

    if mode == tf.estimator.ModeKeys.EVAL:
        return tf.estimator.EstimatorSpec(mode, loss=loss, eval_metric_ops={'accuracy': accuracy})
    
    assert mode == tf.estimator.ModeKeys.TRAIN

    optimizer = tf.train.AdagradOptimizer(learning_rate=ec.get(t).get(lr))
    train_op = optimizer.minimize(loss, global_step=tf.train.get_global_step())
    return tf.estimator.EstimatorSpec(mode, loss=loss, train_op=train_op)

def train_input_fn(features, labels, batch_size):
    return tf.data.Dataset.from_tensor_slices((dict(features), labels))\
                             .shuffle(1000).repeat().batch(batch_size)
    
def eval_input_fn(features, labels, batch_size):
    return tf.data.Dataset.from_tensor_slices((features, labels)).batch(batch_size)

def z_scores(**kwargs):
    fs = kwargs['data']
    
    return {f: da.z_scores(data=fs[f]) for f in fs.keys()}

def print_scores(**kwargs):
    scores = kwargs['scores']

    for s, data in scores.iteritems():
        mi = min(data)
        mx = max(data)
        print((s, mi, mx, mx - mi))
        
    raw_input()

def run_model(**kwargs):
    avgs, split, labels, feat, ec, t, scs, n, hu, md, ts, ets, bs, rd = kwargs['team_avgs'], kwargs['split'],\
                                                                kwargs['labels'], kwargs['features'],\
                                                                kwargs['estimator_config'], 'train',\
                                                                'saveCheckpointsSteps', 'neurons',\
                                                                'hiddenUnit', 'modelDir', 'trainSteps',\
                                                                'evalThrottleSecs', 'batchSize', 'runDir'

    train_features, train_labels = input_data(game_averages={gid: avgs[gid] for gid in split[0]}, 
                                              labels=labels)
    train_features = z_scores(data=train_features)
    train_features = {tf: train_features[tf] for tf in feat}
    test_features, test_labels = input_data(game_averages={gid: avgs[gid] for gid in split[1]}, 
                                            labels=labels)
    test_features = z_scores(data=test_features)
    test_features = {tf: test_features[tf] for tf in feat}

    feature_cols = []
    for f in feat:
        feature_cols.append(tf.feature_column.numeric_column(key=f))      

    run_config = tf.estimator.RunConfig(save_checkpoints_steps=ec[t][scs])
    classifier = tf.estimator.Estimator(model_fn=model_fn, 
                                        params={'feature_columns': feature_cols, 'estimator_config': ec}, 
                                        config=run_config, 
                                        model_dir=path.join(ec[t][md], "%s_%s" % (str(ec[rd]), 
                                                                                  str(random.randint(0, sys.maxint)))))
    train_spec = tf.estimator.TrainSpec(input_fn=lambda: train_input_fn(train_features, 
                                                                        train_labels, ec[t][bs]), 
                                        max_steps=ec[t][ts])
    eval_spec = tf.estimator.EvalSpec(input_fn=lambda: eval_input_fn(test_features, 
                                                                     test_labels, ec[t][bs]), 
                                      throttle_secs=ec[t][ets])
    tf.estimator.train_and_evaluate(classifier, train_spec, eval_spec)

def evaluate_model(**kwargs):
    ec, data, sp, dp, msd, rd = kwargs['estimator_config'], 'data', 'splitPercent', 'directoryPattern', 'modelSubDir',\
                                'runDir'

    for season_dir in glob.glob(ec[data][dp]):
        gs = temp_lib.game_stats(directory=season_dir)
        team_stats = temp_lib.team_game_stats(directory=season_dir)
        avgs = averages(team_game_stats=team_stats, game_infos=gs, skip_fields=model.UNDECIDED_FIELDS)
        team_stats = {k: team_stats[k] for k in avgs.keys()}        
        labels = tgs.add_labels(team_game_stats=team_stats)        
        histo = histogram_games(game_infos=gs, game_stats=avgs, histo_key='Date')            
        split = stochastic_split_data(game_histo=histo, split_percentage=ec[data][sp],
                              histo_count={k: len(histo[k]) for k in histo.keys()})

        features = da.normal_dists(field_avgs=input_data(game_averages=avgs, labels=labels)[0])\
                     .keys()
        ec.update({rd: "%s_%s" % (ec.get(msd), path.basename(season_dir))})
        run_model(team_avgs=avgs, split=split, labels=labels, features=features, estimator_config=ec)

def read_config(**kwargs):
    ef = kwargs['estimator_file']

    pb = estimator_pb2.Estimator()
    result = {}
    with open(path.abspath(ef), 'rb') as fh:
        proto_str = fh.read()
        text_format.Merge(proto_str, pb)
        result = MessageToDict(pb)
    
    return result

def main(args):
    parser = argparse.ArgumentParser(description='Predict scores of college football games')
    parser.add_argument('--estimator_config')
    args = parser.parse_args() 
    conf_file, c = path.basename(args.estimator_config), 'config'
    dc = '.' + c
      
    if conf_file.endswith(dc):
        est_config = read_config(estimator_file=args.estimator_config)
        est_config.get(c).update({'modelSubDir': conf_file.replace(dc, '')})
        evaluate_model(estimator_config=est_config[c])
    else:
        print("--estimator_config must end with %s" % (str(dc)))

if __name__ == '__main__':
    tf.logging.set_verbosity(tf.logging.INFO)
    tf.app.run(main)
    