/**
 * Selective Preloading Strategy.
 * Source: Phase 6 Implementation Document
 *
 * Preloads routes marked with { data: { preload: true } }
 * to improve perceived performance for critical paths.
 */
import { Injectable } from '@angular/core';
import { PreloadingStrategy, Route } from '@angular/router';
import { Observable, of, timer } from 'rxjs';
import { mergeMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class SelectivePreloadStrategy implements PreloadingStrategy {
  preload(route: Route, load: () => Observable<unknown>): Observable<unknown> {
    // Check if route should be preloaded
    if (route.data?.['preload']) {
      // Delay preloading to not compete with initial load
      const delay = route.data?.['preloadDelay'] || 2000;
      return timer(delay).pipe(mergeMap(() => load()));
    }
    return of(null);
  }
}
