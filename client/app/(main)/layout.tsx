import Navbar from '@/components/navbar'
import React from 'react'

const layout = ({children} : {children: React.ReactNode}) => {
  return (
    <div className='flex-1 w-full flex flex-col gap-20 items-center'>
      <Navbar />
      <main>{children}</main>
    </div>
  )
}

export default layout
