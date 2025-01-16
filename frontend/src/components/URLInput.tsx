import { useState } from 'react';
import { motion } from 'framer-motion';
import { FiSearch } from 'react-icons/fi';

interface URLInputProps {
  onAnalyze: (url: string) => void;
  isLoading: boolean;
}

export const URLInput = ({ onAnalyze, isLoading }: URLInputProps) => {
  const [url, setUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onAnalyze(url.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-input flex flex-col sm:flex-row rounded-xl sm:rounded-2xl p-2 space-y-2 sm:space-y-0"
        >
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter website URL"
            className="flex-1 bg-transparent px-3 sm:px-4 py-2 text-base sm:text-lg text-amber-100 placeholder-amber-200/50 focus:outline-none rounded-lg sm:rounded-none"
            required
          />
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={isLoading}
            className={`flex items-center justify-center sm:justify-start gap-2 rounded-lg sm:rounded-xl px-4 sm:px-6 py-2 text-amber-100 transition-colors w-full sm:w-auto
              ${isLoading
                ? 'cursor-not-allowed bg-amber-900/20'
                : 'bg-gradient-to-r from-amber-600/30 to-orange-600/30 hover:from-amber-600/40 hover:to-orange-600/40'
              }`}
          >
            {isLoading ? (
              <div className="h-4 w-4 sm:h-5 sm:w-5 animate-spin rounded-full border-2 border-amber-100 border-t-transparent" />
            ) : (
              <>
                <FiSearch className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="text-base sm:text-lg">Analyze</span>
              </>
            )}
          </motion.button>
        </motion.div>
      </div>
    </form>
  );
};
