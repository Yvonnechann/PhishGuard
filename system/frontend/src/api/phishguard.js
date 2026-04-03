import axios from 'axios'

export async function analyzeAddress(address) {
  const response = await axios.post('/api/analyze', { address })
  return response.data
}
