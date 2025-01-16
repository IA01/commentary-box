'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Toaster, toast } from 'react-hot-toast'
import { CommentaryModal } from '@/components/CommentaryModal'
import { CommentatorCard } from '@/components/CommentatorCard'
import { URLInput } from '@/components/URLInput'

const commentators = [
  {
    id: 'ravi',
    name: 'Ravi Shastri',
    style: "Ravi's Roast",
  },
  {
    id: 'harsha',
    name: 'Harsha Bhogle',
    style: "Bhogle's Balance",
  },
  {
    id: 'jatin',
    name: 'Jatin Sapru',
    style: "Jatin's Jubilation",
  },
]

export default function Home() {
  const [selectedCommentator, setSelectedCommentator] = useState(commentators[0].id)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [commentary, setCommentary] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleAnalyze = async (url: string) => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          commentator: selectedCommentator,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log('API Response:', data)

      if (!data.commentary) {
        throw new Error('No commentary received from the API')
      }

      setCommentary(data.commentary)
      setIsModalOpen(true)
      toast.success('Analysis complete!')
    } catch (error) {
      console.error('Error during analysis:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to analyze website')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="hero-background" />
      <div className="hero-overlay" />
      
      <div className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-16 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <h1 className="bg-gradient-to-r from-orange-300 via-amber-200 to-yellow-300 bg-clip-text text-4xl font-extrabold text-transparent sm:text-5xl md:text-6xl lg:text-7xl">
            Commentary Box
          </h1>
          <p className="mt-4 text-base sm:text-lg md:text-xl text-amber-100/80">
            Your website analysed in the distinct voice of our commentators
          </p>
        </motion.div>

        <div className="mt-8 sm:mt-12 md:mt-16">
          <h2 className="text-xl sm:text-2xl font-bold text-amber-100">Choose Your Commentator</h2>
          <div className="mt-4 sm:mt-6 grid gap-3 sm:gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {commentators.map((commentator) => (
              <CommentatorCard
                key={commentator.id}
                name={commentator.name}
                style={commentator.style}
                selected={selectedCommentator === commentator.id}
                onClick={() => setSelectedCommentator(commentator.id)}
              />
            ))}
          </div>
        </div>

        <div className="mt-8 sm:mt-12 md:mt-16">
          <URLInput onAnalyze={handleAnalyze} isLoading={isLoading} />
        </div>

        <CommentaryModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          commentary={commentary}
          commentator={commentators.find((c) => c.id === selectedCommentator)?.name || ''}
        />
      </div>
      <Toaster 
        position="bottom-center"
        toastOptions={{
          style: {
            background: 'rgba(255, 255, 255, 0.9)',
            color: '#1a1a1a',
            backdropFilter: 'blur(8px)',
          },
        }}
      />
    </main>
  )
}
