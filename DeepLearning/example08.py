# Exporting model
import tensorflow as tf
import numpy as np
from tensorflow.examples.tutorials.mnist import input_data
import os

work_dir = "./tmp"
model_version = 9
trainning_iteration = 1000
input_size = 784
no_class = 10
batch_size = 100
totoal_batches = 200

tf_example = tf.parse_example(tf.placeholder(tf.string, name='tf_example'),
                              {'x': tf.FixedLenFeature(shape=[784], dtype=tf.float32), })
x_input = tf.identity(tf_example['x'], name='x')

y_input = tf.placeholder(tf.float32, shape=[None, no_class])
weights = tf.Variable(tf.random_normal([input_size, no_class]))
bias = tf.Variable(tf.random_normal([no_class]))

logits = tf.matmul(x_input, weights) + bias

soft_max_cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=y_input,
                                                                 logits=logits)
loss_operation = tf.reduce_mean(soft_max_cross_entropy)

optimiser = tf.train.AdamOptimizer().minimize(loss_operation)

mnist = input_data.read_data_sets("MNIST_data", one_hot=True)

with tf.Session() as session:
    session.run(tf.global_variables_initializer())

    for batch_no in range(totoal_batches):
        mnist_batch = mnist.train.next_batch(batch_size=batch_size)

        _, loss_value = session.run([optimiser, loss_operation],
                                    feed_dict={x_input: mnist_batch[0],
                                               y_input: mnist_batch[1]})

        print(loss_value)

    signature_def = (tf.saved_model.signature_def_utils.build_signature_def(inputs={'x': tf.saved_model.utils.build_tensor_info(x_input)},
                                                                            outputs={'y': tf.saved_model.utils.build_tensor_info(y_input)},
                                                                            method_name="tensorflow/serving/predict"))

    model_path = os.path.join(work_dir, str(model_version))
    saved_model_builder = tf.saved_model.builder.SavedModelBuilder(model_path)

    saved_model_builder.add_meta_graph_and_variables(session, [tf.saved_model.tag_constants.SERVING],
                                                     signature_def_map={'prediction': signature_def},
                                                     legacy_init_op=tf.group(tf.tables_initializer(), name='legacy_init_op'))
    saved_model_builder.save()


# Serning the trained model

from grpc.beta import implementations
import numpy
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2

concurrency = 1
num_tests= 100
host = ""
port = 8000
work_dir = "./tmp"

def _create_rpc_callback():
    def _callback(result):
        response = np.array(result.result().outputs['y'].float_val)
        prediction = np.argmax(response)

        print(prediction)

    return _callback

test_data_set = mnist.test
test_image = mnist.test.images[0]

predict_request = predict_pb2.PredictRequest()
predict_request.model_spec.name = 'mnist'
predict_request.model_spec.signature_name = 'prediction'

predict_channel = implementations.insecure_channel(host, int(port))
predict_stub = prediction_service_pb2.beta_create_PredictionService_stub(predict_channel)

predict_request.inputs['x'].CopyFrom(
    tf.contrib.util.make_tensor_proto(test_image, shape=[1, test_image.size]))
result = predict_stub.Predict.future(predict_request, 3.0)
result.add_done_callback(
    _create_rpc_callback())