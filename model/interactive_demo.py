import pickle
import re
import torch as th
import numpy as np

from process_raw_data import filter_query
from src.batcher import load_meta, prepare_batch_data
from src.model import DocReaderModel
from config import set_args
from src.fetch_realtime_grounding import GroudingGenerator


def pred2words(prediction, vocab):
	EOS_token = 3
	outputs = []
	for pred in prediction:
		new_pred = pred
		for i, x in enumerate(pred):
			if int(x) == EOS_token:
				new_pred = pred[:i]
				break
		outputs.append(' '.join([vocab[int(x)] for x in new_pred]))
	return outputs


class InteractiveModel:
	def __init__(self, args):
		self.is_cuda = args.cuda
		self.embedding, self.opt, self.vocab = load_meta(vars(args), args.meta)
		self.state_dict = th.load(args.model_dir)["state_dict"]
		self.model = DocReaderModel(self.opt, self.embedding, self.state_dict)
		self.model.setup_eval_embed(self.embedding)
		if self.is_cuda:
			self.model.cuda()

	def predict(self, data):
		processed_data = prepare_batch_data([self.preprocess_data(x) for x in data], ground_truth=False)
		prediction, prediction_topks = self.model.predict(processed_data)
		pred_word = pred2words(prediction, self.vocab)
		prediction = [np.asarray(x, dtype=np.str).tolist() for x in pred_word]
		return (prediction, prediction_topks)

	def preprocess_data(self, sample):
		def tok_func(toks):
			return [self.vocab[w] for w in toks]

		fea_dict = {}

		query_tokend = sample['query']
		doc_tokend = sample['fact']

		# TODO
		fea_dict['query_tok'] = tok_func(query_tokend)
		fea_dict['query_pos'] = []
		fea_dict['query_ner'] = []

		fea_dict['doc_tok'] = tok_func(doc_tokend)
		fea_dict['doc_pos'] = []
		fea_dict['doc_ner'] = []
		fea_dict['doc_fea'] = ''

		if len(fea_dict['query_tok']) == 0:
			fea_dict['query_tok'] = [0]
		if len(fea_dict['doc_tok']) == 0:
			fea_dict['doc_tok'] = [0]

		return fea_dict


if __name__ == "__main__":
	args = set_args()
	m = InteractiveModel(args)
	conversation = "hey there, what is up? I love Nokia phones."
	# Generate grounding for given conversation
	g = GroudingGenerator()
	grounding = " ".join(g.get_grounding_data(conversation))
	# Generate predictions
	data = [{'query': conversation, 'fact': grounding}]
	print(m.predict(data)[0])