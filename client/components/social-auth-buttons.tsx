
import React from 'react'
import Image from 'next/image'
import { createClient } from '@/lib/supabase/client'

type Provider = 'google' | 'github'

type ProviderType = {
  name: Provider
  label: string
  icon: string
  size: number
}

const providers: ProviderType[] = [
  { name: 'google', label: 'Continue with Google', icon: '/google.png', size: 30 },
  { name: 'github', label: 'Continue with GitHub', icon: '/github.svg', size: 32 },
]

export default function SocialAuthButtons() {
  const supabase = createClient()

  const handleOauthLogin = async (provider: Provider) => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })

    if (error) console.error(error)
  }

  return (
    <div className="space-y-2">
      {providers.map((p) => (
        <button
          key={p.name}
          type="button"
          onClick={() => handleOauthLogin(p.name)}
          className="w-full flex items-center gap-3 rounded-md border px-4 py-3 hover:bg-gray-50"
        >
          <Image src={p.icon} alt={p.name} width={p.size} height={p.size} />
          <span>{p.label}</span>
        </button>
      ))}
    </div>
  )
}