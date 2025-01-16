import { Dialog } from '@headlessui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiShare2, FiCopy } from 'react-icons/fi';
import { toast } from 'react-hot-toast';

interface CommentaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  commentary: string;
  commentator: string;
}

export const CommentaryModal = ({ isOpen, onClose, commentary, commentator }: CommentaryModalProps) => {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(commentary);
    toast.success('Commentary copied to clipboard!');
  };

  const handleShare = async () => {
    try {
      await navigator.share({
        title: `Cricket Commentary by ${commentator}`,
        text: commentary,
      });
    } catch (err) {
      toast.error('Sharing failed. Try copying instead!');
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <Dialog
          open={isOpen}
          onClose={onClose}
          className="relative z-50"
        >
          <div className="fixed inset-0 bg-black/60" aria-hidden="true" />

          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Dialog.Panel className="w-full max-w-xl transform overflow-hidden rounded-xl bg-gradient-to-br from-gray-900 to-gray-800 p-6 shadow-xl transition-all">
              <div className="mb-4 flex items-center justify-between">
                <Dialog.Title className="text-xl font-bold text-white">
                  {commentator}'s Take
                </Dialog.Title>
                <button
                  onClick={onClose}
                  className="rounded-full p-2 text-gray-400 hover:bg-gray-700 hover:text-white"
                >
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              <div className="max-h-[60vh] overflow-y-auto rounded-lg bg-gray-800/50 p-4">
                <p className="whitespace-pre-wrap text-lg text-white">{commentary || 'Loading commentary...'}</p>
              </div>

              <div className="mt-4 flex justify-end space-x-2">
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={handleCopy}
                  className="flex items-center space-x-1 rounded-full bg-gray-700 px-4 py-2 text-gray-300 hover:bg-gray-600"
                >
                  <FiCopy className="h-5 w-5" />
                  <span>Copy</span>
                </motion.button>
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={handleShare}
                  className="flex items-center space-x-1 rounded-full bg-gray-700 px-4 py-2 text-gray-300 hover:bg-gray-600"
                >
                  <FiShare2 className="h-5 w-5" />
                  <span>Share</span>
                </motion.button>
              </div>
            </Dialog.Panel>
          </div>
        </Dialog>
      )}
    </AnimatePresence>
  );
};