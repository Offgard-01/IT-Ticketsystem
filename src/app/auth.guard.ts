// auth.guard.ts

import { Injectable } from '@angular/core';
import {
  CanActivate,
  Router,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  UrlTree
} from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): boolean | UrlTree {
    const expectedRole = route.data['expectedRole'];

    if (!this.authService.isLoggedIn()) {
      // Benutzer ist nicht angemeldet
      return this.router.parseUrl('/login');
    }

    if (expectedRole && !this.authService.hasRole(expectedRole)) {
      // Benutzer hat nicht die erforderliche Rolle
      // Optional: Leiten Sie den Benutzer auf eine "Zugriff verweigert"-Seite weiter
      // return this.router.parseUrl('/access-denied');
      // Oder leiten Sie zur Login-Seite um
      return this.router.parseUrl('/login');
    }

    return true;
  }
}
