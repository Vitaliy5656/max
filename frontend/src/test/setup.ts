/**
 * Vitest setup file for React Testing Library
 */
import '@testing-library/jest-dom'

// Mock scrollTo for jsdom
Element.prototype.scrollTo = () => { }
Element.prototype.scrollIntoView = () => { }
window.scrollTo = () => { }
