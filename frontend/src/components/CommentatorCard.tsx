import Image from 'next/image';
import { motion } from 'framer-motion';

interface CommentatorCardProps {
  name: string;
  selected: boolean;
  onClick: () => void;
  style: string;
}

interface CommentatorStyle {
  bgGradient: string;
  emoji: string;
  image: string;
  imagePosition: string;
  imageStyle?: string;
}

const commentatorStyles: Record<string, CommentatorStyle> = {
  'Ravi Shastri': {
    bgGradient: 'bg-gradient-to-br from-orange-600/20 to-red-800/20',
    emoji: '🎯',
    image: '/commentators/ravi-shastri.png',
    imagePosition: 'object-[50%_25%]',
    imageStyle: 'bg-gray-900'
  },
  'Harsha Bhogle': {
    bgGradient: 'bg-gradient-to-br from-amber-600/20 to-yellow-800/20',
    emoji: '🎙️',
    image: '/commentators/harsha-bhogle.jpeg',
    imagePosition: 'object-[50%_30%]',
    imageStyle: 'bg-gray-900'
  },
  'Jatin Sapru': {
    bgGradient: 'bg-gradient-to-br from-yellow-600/20 to-orange-800/20',
    emoji: '⚡',
    image: '/commentators/jatin-sapru.jpeg',
    imagePosition: 'object-[50%_30%]'
  }
};

export const CommentatorCard = ({ name, selected, onClick, style }: CommentatorCardProps) => {
  const commentatorStyle = commentatorStyles[name as keyof typeof commentatorStyles];

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`commentator-card relative cursor-pointer rounded-xl p-4 sm:p-5 md:p-6 ${commentatorStyle.bgGradient} 
        ${selected ? 'selected' : ''} 
        transition-all duration-300 ease-in-out`}
    >
      <div className="flex items-center space-x-3 sm:space-x-4">
        <div className={`relative h-12 w-12 sm:h-14 sm:w-14 md:h-16 md:w-16 overflow-hidden rounded-full ring-2 ring-amber-300/30 ${commentatorStyle.imageStyle || ''}`}>
          <Image
            src={commentatorStyle.image}
            alt={name}
            width={64}
            height={64}
            className={`rounded-full ${commentatorStyle.imagePosition} w-full h-full`}
            priority
            quality={90}
          />
        </div>
        <div className="flex flex-col">
          <span className="text-lg sm:text-xl md:text-2xl font-bold text-amber-100">
            {commentatorStyle.emoji} {name}
          </span>
          <span className="text-sm sm:text-base md:text-lg font-medium text-amber-200/80">
            {style}
          </span>
        </div>
      </div>
      {selected && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -right-1.5 -top-1.5 sm:-right-2 sm:-top-2 rounded-full bg-amber-400 p-1.5 sm:p-2"
        >
          <svg
            className="h-3 w-3 sm:h-4 sm:w-4 text-gray-900"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M5 13l4 4L19 7" />
          </svg>
        </motion.div>
      )}
    </motion.div>
  );
}; 