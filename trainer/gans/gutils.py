import os
import itertools

import torch
import numpy as np
import matplotlib.pyplot as plt
from torch.autograd import Variable


def save_results(args, images, name, is_tensor=False, axis_size=10, experiment=None):
    '''
    Saves the images in a grid of axis_size * axis_size
    '''
    axis_size = int(axis_size)
    _, sub = plt.subplots(axis_size, axis_size, figsize=(5, 5))
    for i, j in itertools.product(range(axis_size), range(axis_size)):
        sub[i, j].get_xaxis().set_visible(False)
        sub[i, j].get_yaxis().set_visible(False)

    for k in range(axis_size * axis_size):
        i = k // axis_size
        j = k % axis_size
        sub[i, j].cla()
        if args.dataset == "CIFAR100" or args.dataset == "CIFAR10":
            if is_tensor:
                sub[i, j].imshow((images[k].cpu().numpy().transpose(1, 2, 0) + 1)/2)
            else:
                sub[i, j].imshow((images[k].cpu().data.numpy().transpose(1, 2, 0) + 1)/2)
        elif args.dataset == "MNIST":
            if is_tensor:
                sub[i, j].imshow(images[k, 0].cpu().numpy(), cmap='gray')
            else:
                sub[i, j].imshow(images[k, 0].cpu().data.numpy(), cmap='gray')

    plt.savefig(experiment.path + "results/" + name + ".png")
    plt.cla()
    plt.clf()
    plt.close()


def generate_examples(
        args, G, num_examples, active_classes, total_classes,
        fixed_noise, experiment, name="", save=False, is_cond=False):
    '''
    Returns a dict[class] of generated samples.
    In case of Non-Conditional GAN, the samples in the dict are random, they do
    not correspond to the keys in the dict
    Just passing in random noise to the generator and storing the results in dict
    '''
    G.eval()
    examples = {}
    for idx, klass in enumerate(active_classes):
        # Generator outputs 100 images at a time
        for _ in range(num_examples//100):
            #TODO refactor these conditionals
            if is_cond:
                targets = torch.zeros(100, total_classes, 1, 1)
                targets[:, klass] = 1
            if args.cuda:
                targets = Variable(targets.cuda(), volatile=True) if is_cond else None
            images = G(fixed_noise, targets) if is_cond else G(fixed_noise)
            if not klass in examples.keys():
                examples[klass] = images
            else:
                examples[klass] = torch.cat((examples[klass],images), dim=0)

        # Dont save more than the required number of classes
        if save and idx <= args.gan_save_classes:
            save_results(args, examples[klass][0:100],
                         name + "_C" + str(klass),
                         False, 10, experiment)
    return examples


def save_gan_losses(g_loss, d_loss, epochs, increment, experiment, name='GAN_LOSS'):
    print(g_loss)
    print(d_loss)
    x = range(len(g_loss))
    plt.plot(x, g_loss, label='G_loss')
    plt.plot(x, d_loss, label='D_loss')

    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend(loc=4)
    plt.grid(True)
    plt.xlim((0, epochs))

    plt.savefig(experiment.path + name + "_" + str(increment) + ".png")
    plt.cla()
    plt.clf()
    plt.close()


def save_checkpoint(epoch, increment, experiment, G):
    '''
    Saves Generator
    '''
    if epoch == 0:
        return
    print("[*] Saving Generator checkpoint")
    path = experiment.path + "checkpoints/"
    torch.save(G.state_dict(),
               '{0}G_inc_{1}_e_{2}.pth'.format(path, increment, epoch))


def load_checkpoint(g_ckpt_path, increment, G):
    '''
    Loads the latest generator for given increment
    g_ckpt_path = self.args.load_g_ckpt
    '''
    max_e = -1
    filename = None
    for f in os.listdir(g_ckpt_path):
        vals = f.split('_')
        incr = int(vals[2])
        epoch = int(vals[4].split('.')[0])
        if incr == increment and epoch > max_e:
            max_e = epoch
            filename = f
    if max_e == -1:
        print('[*] Failed to load checkpoint')
        return False
    path = os.path.join(g_ckpt_path, filename)
    G.load_state_dict(torch.load(path))
    print('[*] Loaded Generator from %s' % path)
    return True


def update_lr(epoch, g_opt, d_opt, gan_schedule, gan_gammas):
    for temp in range(0, len(gan_schedule)):
        if gan_schedule[temp] == epoch:
            #Update Generator LR
            for param_group in g_opt.param_groups:
                current_lr_g = param_group['lr']
                param_group['lr'] = current_lr_g * gan_gammas[temp]
                print("Changing GAN Generator learning rate from",
                      current_lr_g, "to", current_lr_g * gan_gammas[temp])
            #Update Discriminator LR
            for param_group in d_opt.param_groups:
                current_lr_d = param_group['lr']
                param_group['lr'] = current_lr_d * gan_gammas[temp]
                print("Changing GAN Discriminator learning rate from",
                      current_lr_d, "to", current_lr_d * gan_gammas[temp])
